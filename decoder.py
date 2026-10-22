"""Offline OM capture decoder. No network access or amplifier commands."""
import struct, socket, math, re, json
from pathlib import Path

def packets(path,host=None,port=10001):
    b=Path(path).read_bytes(); pos=0; endian='<'; interfaces=[]
    while pos+12<=len(b):
        if b[pos:pos+4]==b'\x0a\x0d\x0d\x0a':
            endian='<' if b[pos+8:pos+12]==b'\x4d\x3c\x2b\x1a' else '>'; interfaces=[]
        typ,n=struct.unpack_from(endian+'II',b,pos)
        if n<12 or pos+n>len(b) or struct.unpack_from(endian+'I',b,pos+n-4)[0]!=n: raise ValueError('Invalid capture block')
        d=b[pos+8:pos+n-4];pos+=n
        if typ==1:
            link=struct.unpack_from(endian+'H',d)[0]; resolution=1e-6; off=8
            while off+4<=len(d):
                code,size=struct.unpack_from(endian+'HH',d,off);v=d[off+4:off+4+size];off+=4+((size+3)//4)*4
                if code==9 and v: resolution=(2 if v[0]&128 else 10)**(-(v[0]&127))
                if code==0:break
            interfaces.append((link,resolution))
        if typ!=6:continue
        iface,hi,lo,cap,_=struct.unpack_from(endian+'IIIII',d);p=d[20:20+cap];link,res=interfaces[iface]
        if link!=1 or len(p)<34 or p[12:14]!=b'\x08\x00':continue
        ip=p[14:];total=struct.unpack_from('!H',ip,2)[0];ip=ip[:total];h=(ip[0]&15)*4
        if len(ip)<h+20 or ip[9]!=6:continue
        src=socket.inet_ntoa(ip[12:16]);dst=socket.inet_ntoa(ip[16:20]);tcp=ip[h:];sp,dp,seq=struct.unpack_from('!HHI',tcp);payload=tcp[(tcp[12]>>4)*4:]
        if (host is None or src==host) and sp==port and payload:
            yield ((hi<<32)|lo)*res,(src,sp,dst,dp),seq,payload

class Decoder:
    def __init__(self):self.tokens=[];self.measurement_revision=0;self.field_revisions={};self.buffer=b'';self.state={ 'status':'Unknown','transmitting':False,'forward':None,'reflected':None,'swr':None }
    def feed(self,data):
        self.tokens=[];self.buffer+=data; updates=[]
        while self.buffer:
            if self.buffer[0]==61:
                if len(self.buffer)<10:break
                if self.buffer[9]!=59:raise ValueError('Malformed binary measurement')
                v=self.buffer[1:9];self.buffer=self.buffer[10:]
                self.measurement_revision+=1
                self.state['rf_idle_confirmed']=False
                f=int.from_bytes(v[:2],'little');r=v[2]*2
                ratio=math.sqrt(r/f) if f>r and f>0 else None
                self.state.update(transmitting=(self.state.get('transmitting',False) or f>0 or v[3]>0),forward=f,reflected=r,input=v[3],swr=(1+ratio)/(1-ratio) if ratio is not None else None,raw=v.hex(),screen_ma=int.from_bytes(v[4:5],'little',signed=True))
                self.mark('screen_ma')
                self.state['gain_db']=10*math.log10(f/v[3]) if f>0 and v[3]>0 else None
            else:
                end=self.buffer.find(b';')
                if end<0:
                    if len(self.buffer)>512:raise ValueError('Unterminated status message')
                    break
                token=self.buffer[:end].decode('ascii');self.buffer=self.buffer[end+1:]
                self.tokens.append(token)
                if token.startswith('ST') and token!='STBY':self.state['startup_status_reply']=token
                status_match=re.fullmatch(r'ST(\d{4})-.*',token)
                if status_match:
                    self.state['status']={'1100':'Standby','1110':'Operate','2000':'Off'}.get(status_match[1],'Unknown')
                    self.state.pop('countdown',None)
                if token in ('OPERATE','STBY','PAOFF','PAON'):self.state['status']={'OPERATE':'Operate','STBY':'Standby','PAOFF':'Off','PAON':'On'}[token];self.state.pop('countdown',None)
                elif token=='COON':self.state['status']='Cooling down'
                elif re.fullmatch(r'(WA|CO)\d+',token):self.state.update(status='Warming up' if token[:2]=='WA' else 'Cooling down',countdown=int(token[2:]))
                elif token in ('PTTON','PTTOFF'):
                    self.state['transmitting']=token=='PTTON'
                    self.state['rf_idle_confirmed']=token=='PTTOFF'
                    if token=='PTTOFF':
                        self.measurement_revision+=1
                        self.state.update(forward=0,reflected=0,swr=None,input=0,gain_db=None)
                elif re.fullmatch(r'FR\d+',token):
                    self.state['frequency_khz']=int(token[2:]);self.mark('frequency_khz')
                else:
                    m=re.fullmatch(r'(IP|UP|UGA|UGB|US|UHA|UHB|UM|TE)(-?\d+(?:\.\d+)?)',token)
                    if m:
                        key,raw=m.groups();value=float(raw)
                        fields={'IP':('plate_a',.001),'UP':('plate_v',1),'US':('screen_v',1),'UHA':('heater_a_v',1),'UHB':('heater_b_v',1),'UM':('mains_v',1),'TE':('temperature_c',.5),'UGA':('grid_a_v',1),'UGB':('grid_b_v',1)}
                        name,scale=fields[key];self.state[name]=value*scale;self.mark(name)
                self.state['last_status']=token
            updates.append(dict(self.state))
        return updates

    def mark(self,key):self.field_revisions[key]=self.field_revisions.get(key,0)+1

def replay(path):
    dec=Decoder(); expected=None; stream=None; events=[]; start=None
    for t,key,seq,data in packets(path):
        if start is None:start=t
        if stream is None:stream=key
        if key!=stream:raise ValueError('Multiple TCP streams: select one connection first')
        original_end=seq+len(data)
        if expected is not None:
            if seq>expected:raise ValueError('TCP gap or out-of-order packet; reassembly required')
            data=data[max(0,expected-seq):]
        expected=max(expected or original_end,original_end)
        # Captures are in order; retransmitted bytes are ignored.
        if data:
            for state in dec.feed(data):events.append({'time':round(t-start,3),**state})
    if dec.buffer:raise ValueError('Capture ends with a partial message')
    return events

if __name__=='__main__':
    import sys
    print(json.dumps(replay(sys.argv[1])))

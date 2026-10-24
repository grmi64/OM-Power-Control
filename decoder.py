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
    def __init__(self):
        self.tokens=[];self.measurement_revision=0;self.field_revisions={};self.buffer=b'';self.state={ 'status':'Unknown','transmitting':False,'forward':None,'reflected':None,'swr':None }
        self._last_plate_current=None;self._saved_tune_release=False;self._tune_save_seen=False

    def confirm_rf_idle(self,source):
        self._saved_tune_release=False;self.measurement_revision+=1;self.mark('rf')
        self.state.update(transmitting=False,rf_idle_confirmed=True,rf_idle_source=source,forward=0,reflected=0,swr=None,input=0,gain_db=None)
    def feed(self,data):
        self.tokens=[];self.buffer+=data; updates=[]
        while self.buffer:
            # Idle NUL bytes occur between replies. Never strip bytes within a
            # binary frame or inside an ASCII token: both must retain framing.
            if self.buffer[0]==0:
                self.buffer=self.buffer.lstrip(b'\x00');continue
            if self.buffer[0]==61:
                if len(self.buffer)<10:break
                if self.buffer[9]!=59:raise ValueError('Malformed binary measurement')
                v=self.buffer[1:9];self.buffer=self.buffer[10:]
                self.measurement_revision+=1
                self.mark('rf')
                self.state['rf_idle_confirmed']=False
                self.state['rf_idle_source']=None
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
                status_match=re.fullmatch(r'ST(\d{4})-\s*(.*)',token)
                if status_match:
                    code,name=status_match.groups()
                    self.state['antenna_name']=name.strip()[:80]
                    self.state['antenna_number']=int(code[0]) if code[0] in '12' and code[1:] in ('100','110') else None
                    self.state['status']=('Operate' if code[1:]=='110' else 'Standby') if code[0] in '12' and code[1:] in ('100','110') else 'Off' if code=='2000' else 'Unknown'
                    self.state.pop('countdown',None)
                if token=='AUTO':
                    self._last_plate_current=None;self._saved_tune_release=False;self._tune_save_seen=False
                    self.state.update(autotune_phase='entered',autotune_message='Automatic tuning selected',autotune_saved=False,autotune_aborted=False,autotune_stop_reported=False,autotune_abort_origin=None,autotune_defaults=False,autotune_stopped_saved=False)
                elif token=='AUTOESC':self.state.update(autotune_phase='cancelled',autotune_message='Automatic tuning exited',autotune_saved=False)
                elif token.startswith('AUTO:'):
                    message=token[5:].strip()
                    phases={'WAITING FOR INPUT POWER':'waiting','AUTOTUNE IN PROGRESS':'tuning','AUTOTUNE DONE':'succeeded','AUTOTUNE ABORTED':'aborted'}
                    phase=phases.get(message,'unknown')
                    if phase=='aborted':
                        self.state['autotune_aborted']=True
                        self.state['autotune_abort_origin']='stop' if self.state.get('autotune_stop_reported') else 'rf_lost' if self.state.get('rf_idle_confirmed') else 'unknown'
                    if self.state.get('autotune_aborted') and phase in ('waiting','tuning','succeeded'):phase='aborted'
                    self.state.update(autotune_phase=phase,autotune_message=message,autotune_saved=False)
                elif token=='STOP':self.state.update(autotune_phase='aborted',autotune_aborted=True,autotune_stop_reported=True,autotune_abort_origin='stop',autotune_message='Autotune stopped by operator',autotune_saved=False)
                elif token.startswith('AUTO'):
                    self.state.update(autotune_phase='unknown',autotune_message=token[:200],autotune_saved=False)
                elif token=='SAVE DEFAULT' and self.state.get('autotune_phase')=='aborted':self.state.update(autotune_phase='defaults',autotune_message='Amplifier reported default settings saved',autotune_saved=False,autotune_defaults=True)
                elif token=='SAVE USER' and self.state.get('autotune_phase')=='aborted' and self.state.get('autotune_abort_origin')=='stop':self.state.update(autotune_phase='stopped-exited',autotune_message='Amplifier reported user settings saved after Stop',autotune_saved=False,autotune_stopped_saved=True)
                elif token=='SAVE USER' and self.state.get('autotune_phase')=='succeeded':
                    self.state['autotune_saved']=True
                    if not self._tune_save_seen:
                        self._saved_tune_release=True;self._tune_save_seen=True
                elif re.fullmatch(r'(LO|TU|OT)-?\d+',token):
                    # Raw positions only; engineering-unit conversion is not yet validated.
                    prefix=token[:2];self.state[{'LO':'autotune_load_raw','TU':'autotune_tune_raw','OT':'autotune_offset_raw'}[prefix]]=int(token[2:])
                if token in ('OPERATE','STBY','PAOFF','PAON'):self.state['status']={'OPERATE':'Operate','STBY':'Standby','PAOFF':'Off','PAON':'On'}[token];self.state.pop('countdown',None)
                elif token=='COON':self.state['status']='Cooling down'
                elif re.fullmatch(r'(WA|CO)\d+',token):self.state.update(status='Warming up' if token[:2]=='WA' else 'Cooling down',countdown=int(token[2:]))
                elif token in ('PTTON','PTTOFF'):
                    if token=='PTTOFF':self.confirm_rf_idle('ptt-off-message')
                    else:
                        self.mark('rf');self._saved_tune_release=False;self._last_plate_current=None
                        self.state.update(transmitting=True,rf_idle_confirmed=False,rf_idle_source=None)
                elif re.fullmatch(r'FR\d+',token):
                    self.state['frequency_khz']=int(token[2:]);self.mark('frequency_khz')
                else:
                    m=re.fullmatch(r'(IP|UP|UGA|UGB|US|UHA|UHB|UM|TE)(-?\d+(?:\.\d+)?)',token)
                    if m:
                        key,raw=m.groups();value=float(raw)
                        fields={'IP':('plate_a',.001),'UP':('plate_v',1),'US':('screen_v',1),'UHA':('heater_a_v',1),'UHB':('heater_b_v',1),'UM':('mains_v',1),'TE':('temperature_c',.5),'UGA':('grid_a_v',1),'UGB':('grid_b_v',1)}
                        name,scale=fields[key];self.state[name]=value*scale;self.mark(name)
                        if key=='IP' and raw.isdecimal():
                            previous=self._last_plate_current;self._last_plate_current=value
                            # The official remote client has this saved-tune
                            # compatibility path when firmware omits PTTOFF.
                            # Require the current cycle, SAVE USER, and a fresh
                            # positive-to-zero plate-current edge; never time out RF.
                            if self._saved_tune_release and self.state.get('autotune_phase')=='succeeded' and self.state.get('autotune_saved') and not self.state.get('autotune_aborted') and self.state.get('status')=='Operate' and self.state.get('transmitting') is True and previous is not None and previous>0 and value==0:
                                self.confirm_rf_idle('post-tune-current-transition')
                if self.state.get('autotune_phase') in ('cancelled','aborted','unknown','defaults','stopped-exited') or self.state.get('status') in ('Standby','Off','Cooling down','Warming up'):
                    self._saved_tune_release=False
                if token.startswith('AUTO'):self.mark('autotune')
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

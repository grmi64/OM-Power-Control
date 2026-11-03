"""In-memory OM-3501A and OM-4001A protocol simulators. This module never opens a socket.

RF is a simulated operator input, independent of amplifier commands. Values and
timings are synthetic demonstrations, not calibration or hardware validation.
"""
import re,socket,threading,time
from contextlib import contextmanager

class SimulatedAmplifier:
 def __init__(self):
  self.lock=threading.RLock();self.queue=bytearray();self.remote=False
  self.mode='Standby';self.rf=False;self.phase=None;self.abort_origin=None
  self.started=0;self.transition=None;self.sent=[];self.scenario='success'
 def emit(self,data):self.queue.extend(data)
 # Extra simulator controls a model supports; the page shows them only when listed.
 FEATURES=()
 def set_power(self,on):raise ValueError('Simulated power control is not available for this model')
 def inject(self,token):raise ValueError('Simulated alerts are not available for this model')
 def set_input(self,rf,scenario='success'):
  if type(rf) is not bool or scenario not in ('success','unexpected','silence','disconnect'):raise ValueError('Invalid simulation input')
  with self.lock:
   self.scenario=scenario
   if rf!=self.rf:
    self.rf=rf;self.emit(b'PTTON;' if rf else b'PTTOFF;')
    if rf and self.phase=='waiting':
     self.phase='tuning';self.started=time.monotonic();self.emit(b'AUTO:AUTOTUNE IN PROGRESS;')
    elif not rf and self.phase=='tuning':
     self.phase='aborted';self.abort_origin='rf_lost';self.emit(b'AUTO:AUTOTUNE ABORTED;')
 def advance(self):
  now=time.monotonic()
  if self.transition and now>=self.transition[0]:
   self.mode=self.transition[1];self.transition=None;self.emit(b'PAOFF;' if self.mode=='Off' else b'STBY;')
  if self.phase=='tuning' and now-self.started>=4:
   if self.scenario=='success':self.phase='succeeded';self.emit(b'AUTO:AUTOTUNE DONE;SAVE USER;')
   elif self.scenario=='unexpected':self.phase='unknown';self.emit(b'AUTO:SIMULATED UNKNOWN RESPONSE;')
 def sendall(self,data):
  with self.lock:
   self.sent.append(data);self.advance()
   if data==b'C':self.remote=not self.remote;self.emit(b'CON;' if self.remote else b'COFF;')
   elif data==b'?':
    self.emit({'Operate':b'ST1110- SIMULATED ANTENNA;','Standby':b'ST1100- SIMULATED ANTENNA;','Off':b'ST2000- SIMULATED ANTENNA;','Warming up':b'WA3;','Cooling down':b'CO3;'}[self.mode])
    if not self.rf:self.emit(b'PTTOFF;')
   elif data==b'F':self.emit(b'FR14078;')
   elif data==b'1':self.emit(b'INFO:0001,0000001,0,03.21,60,OM3501A;')
   elif data==b'#':
    self.emit(b'IP850;UP2900;US300;UGA75;UGB150;UHA12;UHB12;UM240;TE64;')
    if self.rf:
     forward=700 if self.phase=='tuning' else 1200
     self.emit(b'='+forward.to_bytes(2,'little')+bytes([5,20,2,0,0,0])+b';')
    else:self.emit(b'PTTOFF;')
   elif data==b'O':self.mode='Standby' if self.mode=='Operate' else 'Operate';self.emit(b'STBY;' if self.mode=='Standby' else b'OPERATE;')
   elif data==b'Y':self.mode='Warming up';self.transition=(time.monotonic()+3,'Standby');self.emit(b'PAON;WA3;')
   elif data==b'Z':self.mode='Cooling down';self.transition=(time.monotonic()+3,'Off');self.emit(b'COON;CO3;')
   elif data==b'L':self.phase='entered';self.abort_origin=None;self.emit(b'AUTO;')
   elif data==b'&':self.phase='waiting';self.emit(b'AUTO:WAITING FOR INPUT POWER;')
   elif data==b'8':self.phase='aborted';self.abort_origin='stop';self.emit(b'STOP;AUTO:AUTOTUNE ABORTED;')
   elif data==b'*':
    self.emit(b'SAVE USER;' if self.abort_origin=='stop' else b'SAVE DEFAULT;' if self.phase=='aborted' else b'AUTOESC;');self.phase='cancelled'
   else:raise ValueError('Unsupported simulator command')
 def recv(self,size):
  time.sleep(.03)
  with self.lock:
   self.advance()
   if self.rf and self.scenario=='disconnect':return b''
   if self.rf and self.scenario=='silence':self.queue.clear();raise socket.timeout()
   if not self.queue:raise socket.timeout()
   data=bytes(self.queue[:size]);del self.queue[:size];return data


class Simulated4001A(SimulatedAmplifier):
    """OM-4001A simulator. Wire behavior follows the manufacturer's protocol document (rev.4) and a real
    warm-up capture: no antenna switch (ST0000/ST0100/ST0110), a WAx countdown each second, no PTTOFF
    polling noise, and # replies only every ~3.2 s however often they are requested. Operate-mode and
    RF telemetry, cooling temperatures and the alert messages are synthetic: not calibration or validation.
    """
    FEATURES=('power','alert')
    ANTENNA=b'- NO ANTENNA SWITCH;'
    REPLY_GAP=3.2
    ALERT=re.compile(r'(WG|FA)([1-9]|1[0-5])|HF|HVF|FERROR|CLEAR')
    def __init__(self,warmup_seconds=180,cooldown_seconds=45,clock=time.monotonic,start='Off'):
        super().__init__();self.clock=clock;self.warmup=warmup_seconds;self.cooldown=cooldown_seconds
        self.mode=start;self.mode_started=clock();self.countdown=None;self.last_batch=None;self.last_temp=None;self.hard_fault=None
    def _begin(self,mode):self.mode=mode;self.mode_started=self.clock()
    def set_power(self,on):
        with self.lock:
            self.advance()
            if on and self.mode=='Off':self._start_warmup()
            elif not on and self.mode in ('Standby','Operate'):self._start_cooldown()
    def inject(self,token):
        if not isinstance(token,str) or not self.ALERT.fullmatch(token):raise ValueError('Unsupported simulated alert')
        with self.lock:
            if token=='CLEAR':self.hard_fault=None;return     # what resetting the fault on the amplifier does
            if token=='HF':self.hard_fault=self.clock()       # the amplifier repeats HF once per second until reset
            self.emit(token.encode('ascii')+b';')
    def _start_warmup(self):
        self._begin('Warming up');self.countdown=self.warmup;self.emit(b'WA%d;'%self.warmup)
    def _start_cooldown(self):
        self._begin('Cooling down');self.last_temp=None;self.emit(b'COON;')
    def advance(self):
        super().advance()
        now=self.clock()
        if self.hard_fault is not None and now-self.hard_fault>=1.0:self.hard_fault=now;self.emit(b'HF;')
        elapsed=now-self.mode_started
        if self.mode=='Warming up':
            # One WAx per second, as the amplifier sends them, then PAON and Standby.
            while self.countdown>max(1,self.warmup-int(elapsed)):self.countdown-=1;self.emit(b'WA%d;'%self.countdown)
            if elapsed>=self.warmup:self._begin('Standby');self.countdown=None;self.emit(b'PTTOFF;PAON;STBY;')
        elif self.mode=='Cooling down':
            # CTx (degrees C) until the tube is below 40 C, then PAOFF.
            temp=max(40,55-int(15*elapsed/max(self.cooldown,1)))
            if temp!=self.last_temp and temp>40:self.last_temp=temp;self.emit(b'CT%d;'%temp)
            if elapsed>=self.cooldown:self._begin('Off');self.emit(b'PAOFF;')
    def _real_seconds(self):
        """Elapsed seconds in the capture's 180 s warm-up timescale."""
        return (self.clock()-self.mode_started)*180/max(self.warmup,1)
    def batch(self):
        if self.mode in ('Off','Cooling down'):
            values=(0,0,139,139,0,'0.0','0.0',244,68)
        elif self.mode=='Warming up':
            r=self._real_seconds();heater='%.1f'%(8.0+0.9*min(1,r/35)) if r>=2 else '0.0'
            values=(0,(1564+min(10,int(r/12)) if r<170 else 3215+min(30,int(r-170)*3)) if r>=2 else 0,128,128,19 if r>=2 else 0,heater,heater,244,68)
        else:
            held=self.clock()-self.mode_started
            values=(0,3241+min(14,int(held/4)),140,141,19,'9.0','9.0',244,67)
            if self.rf:values=(1400,3150,140,141,300,'9.0','9.0',244,67)
        return b'IP%d;UP%d;UGA%d;UGB%d;US%d;UHA%s;UHB%s;UM%d;TE%d;'%(values[0],values[1],values[2],values[3],values[4],values[5].encode(),values[6].encode(),values[7],values[8])
    def sendall(self,data):
        with self.lock:
            if data==b'?':
                self.sent.append(data);self.advance()
                code={'Operate':b'ST0110','Standby':b'ST0100'}.get(self.mode,b'ST0000')
                self.emit(code+self.ANTENNA)
            elif data==b'#':
                self.sent.append(data);self.advance();now=self.clock()
                # The amplifier answers this poll only about every 3.2 s, however often it is sent.
                if self.last_batch is None or now-self.last_batch>=self.REPLY_GAP:
                    self.last_batch=now;self.emit(self.batch())
                if self.rf:
                    forward=1700 if self.phase=='tuning' else 2400
                    self.emit(b'='+forward.to_bytes(2,'little')+bytes([5,20,2,0,0,0])+b';')
            elif data==b'F':self.sent.append(data);self.advance();self.emit(b'FR18100;')
            elif data==b'1':self.sent.append(data);self.advance();self.emit(b'INFO:0001,0000001,0000002,03.42,55756,OM4001A;')
            elif data==b'Y':
                self.sent.append(data);self.advance()
                if self.mode=='Off':self._start_warmup()
            elif data==b'Z':
                self.sent.append(data);self.advance()
                if self.mode in ('Standby','Operate'):self._start_cooldown()
            elif data==b'O' and self.mode not in ('Standby','Operate'):
                # The amplifier answers O only when fully on.
                self.sent.append(data);self.advance()
            else:super().sendall(data)

def simulator_for(model):
    """Simulator matching the model label; the OM-3501A one is the default."""
    from profiles import profile
    return Simulated4001A() if profile(model).get('name')=='OM-4001A' else SimulatedAmplifier()

@contextmanager
def simulated_session(amplifier,stop,record):
 from session_protocol import establish,release
 record('OFFLINE simulation: no amplifier socket opened')
 handshake=establish(amplifier,stop,record)
 try:yield amplifier,handshake
 finally:
  # Match the hardware session: failed cleanup must not replace the original
  # telemetry timeout or connection-loss diagnostic.
  try:release(amplifier,record)
  except Exception as exc:record('Remote session close: '+str(exc))

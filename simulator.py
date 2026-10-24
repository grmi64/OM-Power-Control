"""In-memory OM-3501A protocol simulator. This module never opens a socket.

RF is a simulated operator input, independent of amplifier commands. Values and
timings are synthetic demonstrations, not calibration or hardware validation.
"""
import socket,threading,time
from contextlib import contextmanager

class SimulatedAmplifier:
 def __init__(self):
  self.lock=threading.RLock();self.queue=bytearray();self.remote=False
  self.mode='Standby';self.rf=False;self.phase=None;self.abort_origin=None
  self.started=0;self.transition=None;self.sent=[];self.scenario='success'
 def emit(self,data):self.queue.extend(data)
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

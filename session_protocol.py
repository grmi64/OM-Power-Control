"""Connection lifecycle only. C toggles remote communication, never amplifier power."""
import socket,time,threading
from contextlib import contextmanager
from decoder import Decoder

class SessionCancelled(Exception):pass

class ReadOnlySocket:
 """Allow only remote-session lifecycle and verified telemetry requests."""
 ALLOWED=frozenset((b'C',b'?',b'#',b'F'))
 def __init__(self,sock,record=lambda event:None):self._sock=sock;self._record=record
 def sendall(self,data):
  if data not in self.ALLOWED:raise ValueError('Read-only telemetry: operating and tuning commands are blocked')
  self._record('Read-only request: '+data.decode('ascii'));return self._sock.sendall(data)
 def recv(self,size):return self._sock.recv(size)

class TuneTestSocket(ReadOnlySocket):
 """One operator-driven tune with an Operate/Standby pair; power is forbidden."""
 LIMITS={b'O':2,b'L':1,b'&':1,b'8':1,b'*':1}
 def __init__(self,sock,record=lambda event:None,counts=None):
  super().__init__(sock,record);self.counts=counts if counts is not None else {}
 def sendall(self,data):
  if data in self.ALLOWED:return super().sendall(data)
  if data not in self.LIMITS or self.counts.get(data,0)>=self.LIMITS[data]:raise ValueError('RF tune test blocks power, extra tuning and repeated commands')
  if data!=b'O' and self.counts.get(b'O',0)!=1:raise ValueError('Select Operate once before the single tune')
  if data==b'&' and self.counts.get(b'L',0)!=1:raise ValueError('Automatic mode must be selected first')
  if data in (b'8',b'*') and self.counts.get(b'&',0)!=1:raise ValueError('Automatic tuning must be prepared first')
  self.counts[data]=self.counts.get(data,0)+1
  self._record('RF tune-test request: '+data.decode('ascii'));return self._sock.sendall(data)

class ModeTestSocket(ReadOnlySocket):
 """One authorized Operate/Standby pair; no power or tuning bytes."""
 def __init__(self,sock,record=lambda event:None):super().__init__(sock,record);self.toggles=0
 def sendall(self,data):
  if data==b'O':
   if self.toggles>=2:raise ValueError('Operate/Standby test command budget exhausted')
   self.toggles+=1;self._record('Mode-test request: O');return self._sock.sendall(data)
  return super().sendall(data)

class PowerCycleTestSocket(ReadOnlySocket):
 """Exactly one normal shutdown then power-on; never Operate or tuning."""
 def __init__(self,sock,record=lambda event:None):super().__init__(sock,record);self.steps=0
 def sendall(self,data):
  if data in (b'Z',b'Y'):
   sequence=(b'Z',b'Y')
   if self.steps>=len(sequence) or data!=sequence[self.steps]:raise ValueError('Power-cycle test permits one shutdown then one power-on, without retries')
   self.steps+=1;self._record('Power-cycle test request: '+data.decode('ascii'));return self._sock.sendall(data)
  return super().sendall(data)

class ReadinessTestSocket(ReadOnlySocket):
 """One no-RF Operate -> auto-tune ready -> Exit -> Standby sequence."""
 SEQUENCE=(b'O',b'L',b'&',b'*',b'O')
 def __init__(self,sock,record=lambda event:None):super().__init__(sock,record);self.steps=0
 def sendall(self,data):
  if data in ReadOnlySocket.ALLOWED:return super().sendall(data)
  if self.steps>=len(self.SEQUENCE) or data!=self.SEQUENCE[self.steps]:raise ValueError('No-RF readiness test blocked an unauthorized, repeated or out-of-order command')
  self.steps+=1;self._record('No-RF readiness test request: '+data.decode('ascii'));return self._sock.sendall(data)

def acknowledgement(sock,stop,timeout=3,record=lambda event:None):
 decoder=Decoder();received=b'';deadline=time.monotonic()+timeout;reply=None
 while time.monotonic()<deadline:
  if stop.is_set():raise SessionCancelled('Connection cancelled')
  try:chunk=sock.recv(4096)
  except socket.timeout:continue
  if not chunk:raise ConnectionError('Amplifier closed the connection during session setup')
  received+=chunk
  if len(received)>32768:raise ValueError('Unexpected connection acknowledgement')
  decoder.feed(chunk)
  replies=[token for token in decoder.tokens if token in ('CON','COFF')]
  if replies:
   reply=replies[-1];record('Remote session reply: '+' -> '.join(replies))
  # TCP can combine ON/OFF replies or split a later OFF after a complete ON.
  # Use the latest complete state, waiting for any partial session reply.
  partial=decoder.buffer and any(token.startswith(decoder.buffer) for token in (b'CON;',b'COFF;'))
  if reply and not partial:return reply,received
 raise TimeoutError('No connection acknowledgement')

def establish(sock,stop,record=lambda event:None):
 sock.sendall(b'C');reply,data=acknowledgement(sock,stop,record=record)
 if reply=='COFF':
  record('Existing remote session cleared (COFF)')
  # The amplifier explicitly confirmed OFF: one further C establishes ON.
  if stop.is_set():raise SessionCancelled('Connection cancelled')
  sock.sendall(b'C');reply,more=acknowledgement(sock,stop,record=record);data+=more
 if reply!='CON':raise ConnectionError('Amplifier did not enter the remote session')
 record('Remote session connected (CON)');return data

def release(sock,record=lambda event:None):
 sock.sendall(b'C');reply,_=acknowledgement(sock,threading.Event(),timeout=1,record=record)
 if reply=='CON':
  record('Remote session was already off; closing confirmed ON session')
  sock.sendall(b'C');reply,_=acknowledgement(sock,threading.Event(),timeout=1,record=record)
 if reply!='COFF':raise ConnectionError('Remote session close was not confirmed')
 record('Remote session disconnected (COFF)')

@contextmanager
def amplifier_session(endpoint,stop,record=lambda event:None,read_only=False,mode_test=False,power_test=False,readiness_test=False,trace=None):
 if sum(map(bool,(read_only,mode_test,power_test,readiness_test)))>1:raise ValueError('Choose one amplifier access policy')
 with socket.create_connection(endpoint,timeout=3) as sock:
  sock.settimeout(.2);record('TCP connected')
  if trace is not None:
   from wire_trace import TracedSocket
   sock=TracedSocket(sock,trace)
  if readiness_test:sock=ReadinessTestSocket(sock,record)
  elif power_test:sock=PowerCycleTestSocket(sock,record)
  elif mode_test:sock=ModeTestSocket(sock,record)
  elif read_only:sock=ReadOnlySocket(sock,record)
  if stop.wait(.6):raise SessionCancelled('Connection cancelled')
  data=establish(sock,stop,record)
  try:yield sock,data
  finally:
   try:release(sock,record)
   except Exception as e:record('Remote session close: '+str(e))

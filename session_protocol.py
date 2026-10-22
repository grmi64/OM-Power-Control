"""Connection lifecycle only. C toggles remote communication, never amplifier power."""
import socket,time,threading
from contextlib import contextmanager
from decoder import Decoder

class SessionCancelled(Exception):pass

def acknowledgement(sock,stop,timeout=3):
 decoder=Decoder();received=b'';deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  if stop.is_set():raise SessionCancelled('Connection cancelled')
  try:chunk=sock.recv(4096)
  except socket.timeout:continue
  if not chunk:raise ConnectionError('Amplifier closed the connection during session setup')
  received+=chunk
  if len(received)>32768:raise ValueError('Unexpected connection acknowledgement')
  decoder.feed(chunk)
  for token in decoder.tokens:
   if token in ('CON','COFF'):return token,received
 raise TimeoutError('No connection acknowledgement')

def establish(sock,stop,record=lambda event:None):
 sock.sendall(b'C');reply,data=acknowledgement(sock,stop)
 if reply=='COFF':
  record('Existing remote session cleared (COFF)')
  # The amplifier explicitly confirmed OFF: one further C establishes ON.
  if stop.is_set():raise SessionCancelled('Connection cancelled')
  sock.sendall(b'C');reply,more=acknowledgement(sock,stop);data+=more
 if reply!='CON':raise ConnectionError('Amplifier did not enter the remote session')
 record('Remote session connected (CON)');return data

def release(sock,record=lambda event:None):
 sock.sendall(b'C');reply,_=acknowledgement(sock,threading.Event(),timeout=1)
 if reply=='CON':
  record('Remote session was already off; closing confirmed ON session')
  sock.sendall(b'C');reply,_=acknowledgement(sock,threading.Event(),timeout=1)
 if reply!='COFF':raise ConnectionError('Remote session close was not confirmed')
 record('Remote session disconnected (COFF)')

@contextmanager
def amplifier_session(endpoint,stop,record=lambda event:None):
 with socket.create_connection(endpoint,timeout=3) as sock:
  sock.settimeout(.2);record('TCP connected')
  if stop.wait(.6):raise SessionCancelled('Connection cancelled')
  data=establish(sock,stop,record)
  try:yield sock,data
  finally:
   try:release(sock,record)
   except Exception as e:record('Remote session close: '+str(e))

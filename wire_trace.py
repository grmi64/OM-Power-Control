"""Opt-in private wire diagnostics. Observes bytes; never creates commands."""
import json,logging,threading,time
from datetime import datetime,timezone
from pathlib import Path

class WireTrace:
 def __init__(self,path,max_bytes=10*1024*1024):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  self.file=self.path.open('x',encoding='utf-8');self.lock=threading.Lock();self.started=time.monotonic();self.size=0;self.max_bytes=max_bytes
 def record(self,kind,**fields):
  row={'utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-self.started,6),'kind':kind,**fields}
  text=json.dumps(row,ensure_ascii=True)+'\n'
  with self.lock:
   if self.file is None:return
   if self.size+len(text.encode('utf-8'))>self.max_bytes:
    self._close();logging.warning('Telemetry trace reached its size limit; tracing stopped');return
   try:self.file.write(text);self.file.flush();self.size+=len(text.encode('utf-8'))
   except OSError:
    self._close();logging.exception('Telemetry trace write failed; tracing stopped')
 def _close(self):
  try:self.file.close()
  except OSError:pass
  self.file=None
 def close(self):
  with self.lock:
   if self.file is not None:self._close()

class TracedSocket:
 def __init__(self,sock,trace):self.sock=sock;self.trace=trace
 def sendall(self,data):
  started=time.monotonic()
  try:result=self.sock.sendall(data)
  except OSError as exc:
   self.trace.record('tx_error',hex=data.hex(),error=str(exc));raise
  self.trace.record('tx',hex=data.hex(),duration_seconds=round(time.monotonic()-started,6));return result
 def recv(self,size):
  started=time.monotonic()
  try:data=self.sock.recv(size)
  except OSError as exc:
   # Polling timeouts are routine; a recovered gap is visible in RX timestamps.
   import socket
   if not isinstance(exc,socket.timeout):self.trace.record('rx_error',error=str(exc))
   raise
  self.trace.record('rx',hex=data.hex(),duration_seconds=round(time.monotonic()-started,6));return data

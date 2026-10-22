"""Local monitoring prototype. Captured connection/status requests C, ?, and telemetry poll # only."""
import argparse,json,socket,threading,time,secrets,fcntl,tempfile,signal,os
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from decoder import Decoder
SLOW_FIELDS=('plate_a','plate_v','screen_v','heater_a_v','heater_b_v','mains_v','temperature_c','grid_a_v','grid_b_v')
EXTRA_FIELDS=(*SLOW_FIELDS,'screen_ma','frequency_khz')
from controls import Controls
import settings
from collections import deque
from session_protocol import amplifier_session

class Monitor:
 def __init__(self):
  self.lock=threading.Lock();self.stop=threading.Event();self.thread=None;self.settings=settings.load();self.controls=Controls();self.state={'connection':'Disconnected'};self.connection_history=deque(maxlen=32);self.command_history=deque(maxlen=64)
 def snapshot(self):
  with self.lock:s={**self.state,'control':self.controls.view(),'settings':dict(self.settings),'connection_history':list(self.connection_history),'command_history':list(self.command_history)}
  field_times=s.pop('_field_times',{})
  now=time.monotonic();age=now-s.pop('_received',now)
  s['age_seconds']=round(age,1)
  if s['connection']=='Connected' and age>3:s['connection']='Stale'
  measurement_age=now-s.pop('_measurement',0)
  if s['connection']!='Connected':
   s.update(forward=None,reflected=None,swr=None,input=None)
  elif s.get('rf_idle_confirmed') is True and not s.get('transmitting'):
   s.update(forward=0,reflected=0,swr=None,input=0)
  elif measurement_age>3:
   s.update(forward=None,reflected=None,swr=None,input=None)
  for key in EXTRA_FIELDS:
   limit=12 if key=='frequency_khz' else 3
   if s['connection']!='Connected' or now-field_times.get(key,0)>limit:s[key]=None
  s['grid_v']=s['grid_a_v']-s['grid_b_v'] if s.get('grid_a_v') is not None and s.get('grid_b_v') is not None else None
  if s.get('forward') is None or s.get('input') is None:s['gain_db']=None
  return s
 def record_connection(self,event):
  with self.lock:self.connection_history.append({'time':round(time.time(),3),'event':event})
 def connect(self):
  with self.lock:
   if self.thread and self.thread.is_alive():return
   if not self.settings['host']:raise ValueError('Set and save the amplifier address before connecting')
   self.stop.clear();self.controls=Controls();self.state={'connection':'Connecting'}
   self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
 def configure(self,value):
  with self.lock:
   value=settings.validate({**self.settings,**value})
   active=self.thread and self.thread.is_alive()
   if active and any(value[k]!=self.settings[k] for k in ('host','port','model')):raise ValueError('Disconnect before changing amplifier address, port or model')
   self.settings=settings.save(value)
 def configure_display(self,value):
  if not isinstance(value,dict) or set(value)!={'secondary_measurement'}:raise ValueError('Choose a display measurement')
  with self.lock:self.settings=settings.save({**self.settings,**value})
 def trace_command(self,phase,pending,message=''):
  if pending:self.command_history.append({'time':round(time.time(),3),'phase':phase,'source':pending.get('source','standalone'),'action':pending.get('action'),'id':pending.get('id'),'message':message[:300]})
 def command(self,action,key,expected_mode=None,source='standalone'):
  with self.lock:
   pending={'action':str(action)[:20],'id':str(key)[:100],'source':'DXC' if source=='DXC' else 'standalone'}
   try:
    if self.settings.get('model','OM-3501A')!='OM-3501A':raise ValueError('Monitoring only: controls are unverified for this model')
    duplicate=key in self.controls.seen if isinstance(key,str) else False
    self.controls.request(action,key,self.state,expected_mode)
   except ValueError as exc:self.trace_command('rejected',pending,str(exc));raise
   if self.controls.pending and not duplicate:self.controls.pending['source']=pending['source']
   self.trace_command('duplicate ignored' if duplicate else 'queued',pending,self.controls.message)
 def disconnect(self):
  with self.lock:
   self.stop.set()
   if self.thread and self.thread.is_alive():self.state={'connection':'Disconnecting'}
 def run(self):
  dec=Decoder();received=time.monotonic();measurement=0;field_times={}
  try:
   with amplifier_session((self.settings['host'],self.settings['port']),self.stop,self.record_connection) as (sock,handshake):
    dec.feed(handshake)
    sock.sendall(b'?')
    next_poll=0;next_frequency=0;next_status=time.monotonic()+2
    with self.lock:self.state={'connection':'Waiting for amplifier data','_received':received}
    while not self.stop.is_set():
     now=time.monotonic()
     with self.lock:
      previous=self.controls.pending;self.controls.tick()
      if previous and self.controls.pending is None:self.trace_command('uncertain',previous,self.controls.message)
      previous=self.controls.pending;command=self.controls.take(self.state)
      if previous and self.controls.pending is None:self.trace_command('cancelled',previous,self.controls.message)
     if command:
      sock.sendall(command);next_status=now+2
      with self.lock:self.trace_command('sent',self.controls.pending)
     if now>=next_status and not command and not dec.state.get('transmitting') and dec.state.get('status') not in ('Warming up','Cooling down','Off'):
      with self.lock:waiting=self.controls.pending is not None
      if not waiting:sock.sendall(b'?')
      next_status=now+2
     if now>=next_poll:
      sock.sendall(b'#');next_poll=now+1
     with self.lock:waiting=self.controls.pending is not None
     if now>=next_frequency and not command and not waiting:
      sock.sendall(b'F');next_frequency=now+5
     try:data=sock.recv(8192)
     except socket.timeout:
      if time.monotonic()-received>10:raise TimeoutError('No amplifier data for 10 seconds')
      continue
     if not data:raise ConnectionError('Amplifier closed the connection')
     revision=dec.measurement_revision;field_revisions=dict(dec.field_revisions)
     updates=dec.feed(data)
     if updates:
      received=time.monotonic()
      # Only a complete binary frame or explicit transmit-stop confirms fresh power.
      if dec.measurement_revision!=revision:measurement=received
      for key,count in dec.field_revisions.items():
       if field_revisions.get(key)!=count:field_times[key]=received
      with self.lock:
       previous=self.controls.pending;self.controls.observe(dec.tokens)
       if previous and self.controls.pending is None:self.trace_command('uncertain' if self.controls.uncertain else 'confirmed',previous,self.controls.message)
       self.state={**updates[-1],'connection':'Connected','_received':received,'_measurement':measurement,'_field_times':dict(field_times)}
  except Exception as e:
   self.record_connection('Connection ended: '+str(e))
   with self.lock:
    previous=self.controls.pending;self.controls.lost()
    if previous:self.trace_command('uncertain' if self.controls.uncertain else 'cancelled',previous,self.controls.message)
    self.state={'connection':'Disconnected','error':str(e)}
  finally:
   if self.stop.is_set():
    with self.lock:
     previous=self.controls.pending;self.controls.lost()
     if previous:self.trace_command('uncertain' if self.controls.uncertain else 'cancelled',previous,self.controls.message)
     self.state={'connection':'Disconnected'}

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,data,kind='application/json'):
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if self.path=='/':self.send(200,self.server.html.encode(),'text/html; charset=utf-8')
  elif self.path=='/state':self.send(200,json.dumps(self.server.monitor.snapshot()).encode())
  else:self.send(404,b'{}')
 def do_POST(self):
  if self.headers.get('X-OM-Token')!=self.server.token:self.send(403,b'{}');return
  if self.path=='/connect':
   try:self.server.monitor.connect()
   except ValueError as e:
    self.send(409,json.dumps({'error':str(e)}).encode());return
  elif self.path=='/disconnect':self.server.monitor.disconnect()
  elif self.path in ('/settings','/display-settings'):
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=2048:raise ValueError('Invalid settings size')
    value=json.loads(self.rfile.read(size))
    if self.path=='/display-settings':self.server.monitor.configure_display(value)
    else:self.server.monitor.configure(value)
   except (ValueError,TypeError,OSError) as e:
    self.send(409,json.dumps({'error':str(e)}).encode());return
  elif self.path.startswith('/control/'):
   try:
    size=int(self.headers.get('Content-Length','0'))
    if size>1024:raise ValueError('Request too large')
    value=json.loads(self.rfile.read(size))
    self.server.monitor.command(self.path.rsplit('/',1)[-1],value.get('id'),value.get('expected_mode'))
   except (ValueError,TypeError,AttributeError) as e:
    self.send(409,json.dumps({'error':str(e)}).encode());return
  else:self.send(404,b'{}');return
  self.send(200,b'{}')

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=51851);a=p.parse_args()
 # One instance on this computer. No reconnect loop; Windows app must be disconnected separately.
 lock=open(Path(tempfile.gettempdir())/'om3501a-monitor.lock','w')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise SystemExit('Another OM monitor is already running')
 server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);server.monitor=Monitor();server.token=secrets.token_urlsafe(32)
 server.html=Path(__file__).with_name('live.html').read_text().replace('__TOKEN__',server.token).replace('__PRESENTATION__',Path(__file__).with_name('presentation.js').read_text())
 from dxc_feed import start as start_dxc_feed
 try:feed=start_dxc_feed(server.monitor)
 except OSError:feed=None
 print(f'OM monitor: http://127.0.0.1:{server.server_port}',flush=True)
 def terminate(signum,frame):raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,terminate)
 if server.monitor.settings['auto_connect']:server.monitor.connect()
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:
  server.monitor.disconnect()
  if server.monitor.thread:server.monitor.thread.join(4)
  if feed:feed.shutdown();feed.server_close()
  server.server_close();lock.close()
if __name__=='__main__':main()

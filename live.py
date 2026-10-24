"""Local monitoring prototype. Captured connection/status requests C, ?, and telemetry poll # only."""
import argparse,json,socket,threading,time,secrets,tempfile,signal,os
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from decoder import Decoder
SLOW_FIELDS=('plate_a','plate_v','screen_v','heater_a_v','heater_b_v','mains_v','temperature_c','grid_a_v','grid_b_v')
EXTRA_FIELDS=(*SLOW_FIELDS,'screen_ma','frequency_khz')
from controls import Controls
import settings
from collections import deque
from session_protocol import amplifier_session

def readiness_requirement(step,state):
 """Require the exact acknowledged state at each authorized no-RF step."""
 sequence=(('toggle',b'O','Standby',None),('autotune',b'L','Operate',None),('autotune',b'&','Operate',('entered','waiting')),('autotune-exit',b'*','Operate',('waiting',)),('toggle',b'O','Operate',('cancelled',)))
 if not 0<=step<len(sequence):raise ValueError('No-RF readiness test is complete; further commands are blocked')
 action,data,mode,phases=sequence[step]
 if state.get('transmitting') is not False:raise ValueError('No-RF readiness test requires an idle radio')
 if state.get('status')!=mode or (phases is not None and state.get('autotune_phase') not in phases):raise ValueError('No-RF readiness test state changed; no command was sent')
 return action,data,mode if action=='toggle' else None

class Monitor:
 def __init__(self,simulate=False,allow_hardware=False,read_only=False,mode_test=False,power_test=False,readiness_test=False):
  if sum(map(bool,(read_only,mode_test,power_test,readiness_test)))>1:raise ValueError('Choose one amplifier access policy')
  self.lock=threading.Lock();self.stop=threading.Event();self.thread=None;self.settings=settings.load();self.controls=Controls();self.state={'connection':'Disconnected'};self.connection_history=deque(maxlen=32);self.command_history=deque(maxlen=64)
  self.simulate=simulate;self.allow_hardware=allow_hardware;self.read_only=read_only;self.simulator=None
  self.mode_test=mode_test;self.mode_test_sent=0
  self.power_test=power_test;self.power_test_sent=0
  self.readiness_test=readiness_test;self.readiness_test_sent=0
  if simulate:
   from simulator import SimulatedAmplifier
   self.simulator=SimulatedAmplifier();self.settings.update(host='simulation',auto_connect=False,share_dxc=False)
 def snapshot(self):
  with self.lock:s={**self.state,'simulated':self.simulate,'read_only':self.read_only,'mode_test':self.mode_test,'mode_test_sent':self.mode_test_sent,'power_test':self.power_test,'power_test_sent':self.power_test_sent,'readiness_test':self.readiness_test,'readiness_test_sent':self.readiness_test_sent,'control':self.controls.view(),'settings':dict(self.settings),'connection_history':list(self.connection_history),'command_history':list(self.command_history)}
  field_times=s.pop('_field_times',{})
  now=time.monotonic();age=now-s.pop('_received',now)
  s['age_seconds']=round(age,1)
  s['autotune_age_seconds']=round(now-field_times.get('autotune',now),1)
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
   if not self.simulate and not self.allow_hardware:raise ValueError('Hardware access is disabled. Explicit operator approval is required before launching with --hardware.')
   if self.thread and self.thread.is_alive():return
   if self.mode_test and self.mode_test_sent:raise ValueError('Mode test already sent a command; reconnecting cannot reauthorize the test')
   if self.power_test and self.power_test_sent:raise ValueError('Power-cycle test already sent a command; reconnecting cannot reauthorize the test')
   if self.readiness_test and self.readiness_test_sent:raise ValueError('Readiness test already sent a command; reconnecting cannot reauthorize the test')
   if not self.settings['host']:raise ValueError('Set and save the amplifier address before connecting')
   self.stop.clear();self.controls=Controls();self.state={'connection':'Connecting'}
   if self.simulate:
    from simulator import SimulatedAmplifier
    self.simulator=SimulatedAmplifier()
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
    if self.read_only:raise ValueError('Read-only telemetry: operating and tuning commands are blocked')
    if self.readiness_test:
     if source!='standalone' or action not in ('toggle','autotune','autotune-exit'):raise ValueError('No-RF readiness test blocks power, Stop and all unrelated commands')
     duplicate=isinstance(key,str) and key in self.controls.seen
     if not duplicate:
      wanted,_,expected=readiness_requirement(self.readiness_test_sent,self.state)
      if self.readiness_test_sent==2 or action!=wanted or expected_mode!=expected:raise ValueError('No-RF readiness test permits only its next authorized step')
    if self.power_test:
     if action not in ('off','on') or source!='standalone':raise ValueError('Power-cycle test permits only shutdown then power-on; Operate and tuning are blocked')
     duplicate=isinstance(key,str) and key in self.controls.seen
     if not duplicate:
      if self.power_test_sent>=2:raise ValueError('Power-cycle test is complete; further commands are blocked')
      wanted,mode=(('off','Standby'),('on','Off'))[self.power_test_sent]
      if action!=wanted or self.state.get('status')!=mode:raise ValueError('Power-cycle test requires Standby before shutdown and confirmed Off after cooling before power-on')
    if self.mode_test:
     if action!='toggle' or source!='standalone':raise ValueError('Mode test permits only the authorized Operate/Standby pair; power and tuning are blocked')
     duplicate=isinstance(key,str) and key in self.controls.seen
     if not duplicate:
      if self.mode_test_sent>=2:raise ValueError('Operate/Standby test is complete; further commands are blocked')
      if expected_mode!=('Standby' if self.mode_test_sent==0 else 'Operate'):raise ValueError('Mode test requires Standby to Operate, then Operate to Standby')
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
   if self.simulate:
    from simulator import simulated_session
    session=simulated_session(self.simulator,self.stop,self.record_connection)
   else:
    if not self.allow_hardware:raise ValueError('Hardware access is disabled')
    session=amplifier_session((self.settings['host'],self.settings['port']),self.stop,self.record_connection,read_only=self.read_only,mode_test=self.mode_test,power_test=self.power_test,readiness_test=self.readiness_test)
   with session as (sock,handshake):
    if self.readiness_test:
     from session_protocol import ReadinessTestSocket
     if not isinstance(sock,ReadinessTestSocket):sock=ReadinessTestSocket(sock,self.record_connection)
    if self.power_test:
     from session_protocol import PowerCycleTestSocket
     if not isinstance(sock,PowerCycleTestSocket):sock=PowerCycleTestSocket(sock,self.record_connection)
    if self.mode_test:
     from session_protocol import ModeTestSocket
     if not isinstance(sock,ModeTestSocket):sock=ModeTestSocket(sock,self.record_connection)
    if self.read_only:
     from session_protocol import ReadOnlySocket
     if not isinstance(sock,ReadOnlySocket):sock=ReadOnlySocket(sock,self.record_connection)
    dec.feed(handshake)
    # The data timeout starts when session setup completes, not before TCP/setup.
    received=time.monotonic()
    sock.sendall(b'?')
    next_poll=0;next_frequency=0;next_status=time.monotonic()+2
    with self.lock:self.state={'connection':'Waiting for amplifier data','_received':received}
    while not self.stop.is_set():
     now=time.monotonic()
     if now-received>10:raise TimeoutError('No amplifier data for 10 seconds')
     with self.lock:
      previous=self.controls.pending;self.controls.tick()
      if previous and self.controls.pending is None:self.trace_command('uncertain',previous,self.controls.message)
      previous=self.controls.pending;command=None if self.read_only else self.controls.take(self.state)
      if previous and self.controls.pending is None:self.trace_command('cancelled',previous,self.controls.message)
     if command:
      if self.readiness_test:
       _,wanted,_=readiness_requirement(self.readiness_test_sent,self.state)
       if command!=wanted:raise ValueError('No-RF readiness socket policy blocked an unauthorized command')
       self.readiness_test_sent+=1
      if self.power_test:
       if self.power_test_sent>=2:raise ValueError('Power-cycle test command budget exhausted')
       wanted,mode=((b'Z','Standby'),(b'Y','Off'))[self.power_test_sent]
       if command!=wanted or self.state.get('status')!=mode:raise ValueError('Power-cycle socket policy blocked an unauthorized or out-of-order command')
       self.power_test_sent+=1
      if self.mode_test:
       if command!=b'O' or self.mode_test_sent>=2 or self.state.get('status')!=('Standby' if self.mode_test_sent==0 else 'Operate'):raise ValueError('Mode-test socket policy blocked an unauthorized command')
       self.mode_test_sent+=1
      sock.sendall(command);next_status=now+2
      with self.lock:self.trace_command('sent',self.controls.pending)
     if now>=next_status and not command and not dec.state.get('transmitting') and dec.state.get('status') not in ('Warming up','Cooling down','Off') and dec.state.get('autotune_phase') not in ('entered','waiting','tuning','unknown','aborted'):
      with self.lock:waiting=self.controls.pending is not None
      if not waiting:sock.sendall(b'?')
      next_status=now+2
     if now>=next_poll:
      sock.sendall(b'#');next_poll=now+1
     with self.lock:waiting=self.controls.pending is not None
     if now>=next_frequency and not command and not waiting and dec.state.get('autotune_phase') not in ('entered','waiting','tuning','unknown','aborted'):
      sock.sendall(b'F');next_frequency=now+5
     try:data=sock.recv(8192)
     except socket.timeout:
      if time.monotonic()-received>10:raise TimeoutError('No amplifier data for 10 seconds')
      continue
     if not data:raise ConnectionError('Amplifier closed the connection')
     revision=dec.measurement_revision;field_revisions=dict(dec.field_revisions)
     updates=dec.feed(data)
     session_replies=[token for token in dec.tokens if token in ('CON','COFF')]
     if session_replies:
      self.record_connection('Remote session update: '+' -> '.join(session_replies))
      if session_replies[-1]=='COFF':raise ConnectionError('Amplifier remote session closed (COFF); reconnect to re-establish communication')
     # Session acknowledgments alone do not establish live amplifier telemetry.
     if updates and (dec.measurement_revision!=revision or any(token not in ('CON','COFF') for token in dec.tokens)):
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
    self.state={**self.state,'connection':'Disconnected','error':str(e)}
  finally:
   if self.stop.is_set():
    with self.lock:
     previous=self.controls.pending;self.controls.lost()
     if previous:self.trace_command('uncertain' if self.controls.uncertain else 'cancelled',previous,self.controls.message)
     self.state={**self.state,'connection':'Disconnected'}

class Handler(BaseHTTPRequestHandler):
 def setup(self):
  super().setup();self.connection.settimeout(3)
 def log_message(self,*args):pass
 def send(self,status,data,kind='application/json'):
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if self.path=='/':self.send(200,self.server.html.encode(),'text/html; charset=utf-8')
  elif self.path=='/state':self.send(200,json.dumps(self.server.monitor.snapshot()).encode())
  else:self.send(404,b'{}')
 def do_POST(self):
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<=size<=2048:raise ValueError('Invalid request size')
   payload=self.rfile.read(size)
   if len(payload)!=size:raise ValueError('Incomplete request')
  except (ValueError,OSError) as exc:
   self.send(400,json.dumps({'error':str(exc)}).encode());return
  if self.headers.get('X-OM-Token')!=self.server.token:self.send(403,b'{}');return
  if self.path=='/connect':
   try:self.server.monitor.connect()
   except ValueError as e:
    self.send(409,json.dumps({'error':str(e)}).encode());return
  elif self.path=='/disconnect':self.server.monitor.disconnect()
  elif self.path=='/simulation':
   try:
    if not self.server.monitor.simulate:raise ValueError('Simulation controls are disabled in hardware mode')
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=1024:raise ValueError('Invalid simulation input size')
    value=json.loads(payload)
    self.server.monitor.simulator.set_input(value['rf'],value.get('scenario','success'))
   except (ValueError,TypeError,KeyError) as e:
    self.send(409,json.dumps({'error':str(e)}).encode());return
  elif self.path in ('/settings','/display-settings'):
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=2048:raise ValueError('Invalid settings size')
    value=json.loads(payload)
    if self.path=='/display-settings':self.server.monitor.configure_display(value)
    else:self.server.monitor.configure(value)
   except (ValueError,TypeError,OSError) as e:
    self.send(409,json.dumps({'error':str(e)}).encode());return
  elif self.path.startswith('/control/'):
   try:
    size=int(self.headers.get('Content-Length','0'))
    if size>1024:raise ValueError('Request too large')
    value=json.loads(payload)
    self.server.monitor.command(self.path.rsplit('/',1)[-1],value.get('id'),value.get('expected_mode'))
   except (ValueError,TypeError,AttributeError) as e:
    self.send(409,json.dumps({'error':str(e)}).encode());return
  else:self.send(404,b'{}');return
  self.send(200,b'{}')

def create_server(monitor,port=0,preferences=None):
 server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.daemon_threads=True;server.monitor=monitor;server.token=secrets.token_urlsafe(32)
 server.html=Path(__file__).with_name('live.html').read_text(encoding='utf-8').replace('__TOKEN__',server.token).replace('__PRESENTATION__',Path(__file__).with_name('presentation.js').read_text(encoding='utf-8'))
 server.html=server.html.replace('/*__NATIVE_PREFERENCES__*/','window.omPreferences ??= '+json.dumps(preferences or {})+';')
 return server

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=51851)
 mode=p.add_mutually_exclusive_group();mode.add_argument('--simulate',action='store_true');mode.add_argument('--hardware',action='store_true',help='Enable real amplifier access only after explicit operator approval');mode.add_argument('--read-only',action='store_true',help='Real telemetry only; operating and tuning commands blocked')
 a=p.parse_args()
 hardware=a.hardware or a.read_only
 from instance_lock import InstanceLock,READER_MUTEX
 if not hardware:os.environ.setdefault('OM_SETTINGS_PATH',str(settings.data_directory()/'simulation-settings.json'))
 lock=InstanceLock(settings.data_directory()/'instance.lock',name=READER_MUTEX)
 server=create_server(Monitor(simulate=not hardware,allow_hardware=hardware,read_only=a.read_only),a.port)
 from dxc_feed import start as start_dxc_feed
 try:feed=start_dxc_feed(server.monitor) if a.hardware and not a.read_only else None
 except OSError:feed=None
 print(f'OM monitor: http://127.0.0.1:{server.server_port}',flush=True)
 def terminate(signum,frame):raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,terminate)
 if not hardware or server.monitor.settings['auto_connect'] or (a.read_only and server.monitor.settings['host']):server.monitor.connect()
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:
  server.monitor.disconnect()
  if server.monitor.thread:server.monitor.thread.join(4)
  if feed:feed.shutdown();feed.server_close()
  server.server_close();lock.close()
if __name__=='__main__':main()

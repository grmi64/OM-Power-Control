"""Bounded, read-only session diagnostics. Never sends operating/tuning/power bytes.

Traces stay in the ignored .tmp folder and can include local station telemetry.
Close the desktop app first: this tool acquires the same single-reader lock.
"""
import argparse,json,select,socket,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from decoder import Decoder
from instance_lock import InstanceLock,READER_MUTEX
from session_protocol import ReadOnlySocket,establish,release
import settings

def worker_cycle(endpoint,seconds):
 from live import Monitor
 monitor=Monitor(allow_hardware=True,read_only=True)
 monitor.settings={**monitor.settings,'host':endpoint[0],'port':endpoint[1],'auto_connect':False,'share_dxc':False}
 result={'healthy':False,'samples':[]};monitor.connect()
 started=time.monotonic();ready=None
 try:
  while time.monotonic()-started<seconds+6:
   state=monitor.snapshot();now=time.monotonic()
   result['samples'].append({k:state.get(k) for k in ('connection','status','transmitting','age_seconds','error')})
   if state.get('transmitting') or state.get('status') not in (None,'Unknown','Standby'):raise RuntimeError('Amplifier is not in Standby/no RF; diagnostic stopped')
   if state.get('error'):raise RuntimeError(state['error'])
   if state['connection']=='Connected' and state.get('status')=='Standby':
    if ready is None:ready=now
    if state['age_seconds']>3:raise RuntimeError('Stale telemetry during worker diagnostic')
    if now-ready>=seconds:
     result.update(healthy=True,status='Standby',age_seconds=state['age_seconds'],startup_seconds=round(ready-started,3));break
   time.sleep(.5)
  if ready is None:result['error']='No confirmed Standby telemetry'
 except Exception as exc:result['error']=str(exc)
 finally:
  monitor.disconnect();monitor.thread.join(4)
  result['events']=list(monitor.connection_history)
  result['command_count']=len(monitor.command_history)
  if not any(e['event']=='Remote session disconnected (COFF)' for e in monitor.connection_history):result.update(healthy=False,release_error='Clean remote-session closure was not confirmed')
  if monitor.thread.is_alive():result.update(healthy=False,error='Worker did not stop cleanly')
  if monitor.command_history:raise AssertionError('Read-only diagnostic unexpectedly queued a command')
 return result

class RecordedReadOnlySocket(ReadOnlySocket):
 def __init__(self,sock,events):
  super().__init__(sock);self.events=events;self.started=time.monotonic()
 def event(self,kind,**values):self.events.append({'elapsed':round(time.monotonic()-self.started,4),'kind':kind,**values})
 def sendall(self,data):
  if data not in self.ALLOWED:raise AssertionError('Diagnostic attempted an unauthorized amplifier command')
  self.event('tx',ascii=data.decode('ascii'));return super().sendall(data)
 def recv(self,size):
  data=super().recv(size);self.event('rx',hex=data.hex());return data

def cycle(endpoint,seconds):
 result={'events':[],'healthy':False};stop=threading.Event()
 try:
  with socket.create_connection(endpoint,timeout=3) as raw:
   raw.settimeout(.2);wire=RecordedReadOnlySocket(raw,result['events'])
   time.sleep(.6)
   # Inspect pre-command bytes without consuming or altering the stream.
   if select.select([raw],[],[],0)[0]:wire.event('before_first_C',hex=raw.recv(8192,socket.MSG_PEEK).hex())
   data=establish(wire,stop,lambda event:wire.event('session',message=event))
   decoder=Decoder();decoder.feed(data)
   try:
    wire.sendall(b'?');next_poll=0;next_frequency=0;next_status=time.monotonic()+2
    deadline=time.monotonic()+seconds;last_received=time.monotonic();last_standby=None;largest_gap=0;updates=0
    while time.monotonic()<deadline:
     now=time.monotonic()
     if now>=next_status:wire.sendall(b'?');next_status=now+2
     if now>=next_poll:wire.sendall(b'#');next_poll=now+1
     if now>=next_frequency:wire.sendall(b'F');next_frequency=now+5
     try:chunk=wire.recv(8192)
     except socket.timeout:continue
     if not chunk:raise ConnectionError('Peer closed the telemetry socket')
     values=decoder.feed(chunk)
     if values:
      now=time.monotonic();largest_gap=max(largest_gap,now-last_received);last_received=now;updates+=len(values)
      if decoder.state.get('transmitting'):raise RuntimeError('RF detected: diagnostic stopped without operating commands')
      mode=decoder.state.get('status')
      if mode not in ('Unknown','Standby'):raise RuntimeError('Amplifier is not in Standby; diagnostic sent no state-changing commands')
      if mode=='Standby':last_standby=now
    age=time.monotonic()-last_received
    result.update(healthy=last_standby is not None and age<=3 and largest_gap<=3,status=decoder.state.get('status'),age_seconds=round(age,3),largest_gap_seconds=round(largest_gap,3),updates=updates)
   finally:
    try:release(wire,lambda event:wire.event('session',message=event))
    except Exception as exc:result['release_error']=str(exc)
 except Exception as exc:result['error']=str(exc)
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--host',required=True);parser.add_argument('--port',type=int,default=10001)
 parser.add_argument('--cycles',type=int,default=5);parser.add_argument('--observe',type=float,default=13)
 parser.add_argument('--output',type=Path,default=Path('.tmp/reconnect-diagnostic.json'))
 parser.add_argument('--worker',action='store_true',help='Exercise the actual threaded app monitor instead of the direct protocol loop')
 args=parser.parse_args()
 if not 1<=args.cycles<=10 or not 12<=args.observe<=60:parser.error('Use 1-10 cycles with 12-60 seconds observation each')
 endpoint=settings.validate({**settings.DEFAULTS,'host':args.host,'port':args.port})
 args.output.parent.mkdir(parents=True,exist_ok=True)
 results=[]
 with InstanceLock(settings.data_directory()/'instance.lock',name=READER_MUTEX):
  for number in range(1,args.cycles+1):
   print(f'Read-only connection cycle {number}/{args.cycles}',flush=True)
   runner=worker_cycle if args.worker else cycle
   result=runner((endpoint['host'],endpoint['port']),args.observe);results.append(result)
   args.output.write_text(json.dumps({'policy':'read-only C ? # F only; no RF; remain Standby','cycles':results},indent=2),encoding='utf-8')
   print(json.dumps({k:v for k,v in result.items() if k not in ('events','samples')}),flush=True)
   if any('not in Standby' in result.get(key,'') or 'RF detected' in result.get(key,'') for key in ('error',)):break
   if number<args.cycles:time.sleep(1)
 print(f'Healthy cycles: {sum(bool(r["healthy"]) for r in results)}/{len(results)}. Trace: {args.output}',flush=True)
 return 0 if all(r['healthy'] and not r.get('release_error') for r in results) else 1

if __name__=='__main__':raise SystemExit(main())

"""Windows WebView2 host for the shared OM Power Control interface."""
import argparse,json,os,sys,threading,logging
from pathlib import Path
import settings
from instance_lock import InstanceLock,READER_MUTEX
from live import Monitor,create_server

def load_preferences(path):
 try:
  value=json.loads(Path(path).read_text())
  if not isinstance(value,dict):return {}
  return {k:v for k,v in value.items() if k in ('compact','alwaysOnTop') and type(v) is bool or k=='full_size' and isinstance(v,list) and len(v)==2 and all(type(n) is int and 650<=n<=4000 for n in v)}
 except (OSError,ValueError):return {}

class DisplayBridge:
 def __init__(self,path,preferences):
  self._path=Path(path);self._preferences=preferences;self._window=None;self._lock=threading.Lock()
 def display_window(self,options):
  if not isinstance(options,dict) or any(type(options.get(k)) is not bool for k in ('compact','alwaysOnTop')):raise ValueError('Invalid window preferences')
  dispatch=getattr(self,'_dispatch',None)
  if dispatch:dispatch(dict(options))
  else:self._apply(options)
 def _apply(self,options):
  with self._lock:
   small=options['compact'];window=self._window
   changed=small!=self._preferences.get('compact',False)
   if changed and small and window:self._preferences['full_size']=[window.width,window.height]
   size=(420,790) if small else self._preferences.get('full_size',[900,900])
   self._preferences.update(options)
   self._path.parent.mkdir(parents=True,exist_ok=True)
   temp=self._path.with_suffix('.tmp');temp.write_text(json.dumps(self._preferences));os.replace(temp,self._path)
  # Never hold a Python lock while synchronously invoking the Windows UI thread.
  if window:
   window.on_top=options['alwaysOnTop']
   if changed:window.resize(*size)
   window.set_title('OM Power Control · '+('OPERATOR RF TUNE TEST' if getattr(self,'_tune_test',False) else 'NO-RF READINESS TEST' if getattr(self,'_readiness_test',False) else 'POWER-CYCLE TEST' if getattr(self,'_power_test',False) else 'OPERATE / STANDBY TEST' if getattr(self,'_mode_test',False) else 'READ-ONLY TELEMETRY' if getattr(self,'_read_only',False) else 'SIMULATION' if self._simulated else 'Hardware')+(' · Compact' if small else ''))

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 mode=parser.add_mutually_exclusive_group();mode.add_argument('--simulate',action='store_true',help='Offline simulation (default)');mode.add_argument('--hardware',action='store_true',help='Real amplifier access; requires prior explicit operator approval')
 mode.add_argument('--read-only',action='store_true',help='Real telemetry only; all operating and tuning commands blocked')
 mode.add_argument('--tune-test',action='store_true',help='One operator-driven RF tune; power commands blocked')
 mode.add_argument('--readiness-test',action='store_true',help='Explicitly authorized no-RF Operate, auto-tune readiness, Exit and Standby only; power blocked')
 mode.add_argument('--power-test',action='store_true',help='Explicitly authorized shutdown then power-on only; no Operate or tuning')
 mode.add_argument('--mode-test',action='store_true',help='Explicitly authorized Operate then Standby only; two mode commands, no power or tuning')
 parser.add_argument('--host',help='Approved amplifier address for this launch')
 parser.add_argument('--amp-port',type=int,help='Amplifier TCP port for this launch')
 parser.add_argument('--smoke-test',action='store_true',help='Exercise the real WebView2 window offline, then exit')
 parser.add_argument('--trace-telemetry',action='store_true',help='Save private bounded raw amplifier replies and decoder events under local application data')
 args=parser.parse_args(argv)
 if sys.platform!='win32':parser.error('The Windows desktop host requires Windows')
 if args.smoke_test and (args.hardware or args.read_only or args.mode_test or args.power_test or args.readiness_test or args.tune_test):parser.error('Smoke tests must be offline')
 if (args.host or args.amp_port is not None) and not (args.hardware or args.read_only or args.mode_test or args.power_test or args.readiness_test or args.tune_test):parser.error('An amplifier endpoint requires an explicit hardware access mode')
 directory=settings.data_directory();directory.mkdir(parents=True,exist_ok=True)
 logging.basicConfig(filename=directory/'windows.log',level=logging.INFO)
 try:lock=InstanceLock(directory/'instance.lock',name=READER_MUTEX)
 except RuntimeError as exc:
  import ctypes
  ctypes.windll.user32.MessageBoxW(None,str(exc),'OM Power Control',0x40);return 1
 server=feed=None;worker=None;monitor=None;wire_trace_writer=None
 try:
  import webview
  simulated=not (args.hardware or args.read_only or args.mode_test or args.power_test or args.readiness_test or args.tune_test)
  if simulated:os.environ.setdefault('OM_SETTINGS_PATH',str(directory/'simulation-settings.json'))
  preferences=load_preferences(directory/'window.json')
  if args.trace_telemetry:
   from wire_trace import WireTrace
   import time
   wire_trace_writer=WireTrace(directory/('telemetry-trace-'+str(time.time_ns())+'.jsonl'))
   logging.info('Private telemetry trace: %s',wire_trace_writer.path)
  monitor=Monitor(simulate=simulated,allow_hardware=not simulated,read_only=args.read_only,mode_test=args.mode_test,power_test=args.power_test,readiness_test=args.readiness_test,tune_test=args.tune_test,trace=wire_trace_writer)
  if args.host or args.amp_port is not None:
   monitor.settings=settings.validate({**monitor.settings,**({'host':args.host} if args.host else {}),**({'port':args.amp_port} if args.amp_port is not None else {})})
  server=create_server(monitor,preferences=preferences)
  worker=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.1},daemon=True);worker.start()
  if args.hardware and not args.read_only:
   from dxc_feed import start
   try:feed=start(monitor)
   except OSError:logging.exception('DX Caliber feed unavailable')
  if simulated or monitor.settings['auto_connect'] or ((args.read_only or args.mode_test or args.power_test or args.readiness_test or args.tune_test) and monitor.settings['host']):monitor.connect()
  bridge=DisplayBridge(directory/'window.json',preferences);bridge._simulated=simulated
  bridge._read_only=args.read_only
  bridge._mode_test=args.mode_test
  bridge._power_test=args.power_test
  bridge._readiness_test=args.readiness_test
  bridge._tune_test=args.tune_test
  size=(420,790) if preferences.get('compact') else preferences.get('full_size',(900,900))
  url=f'http://127.0.0.1:{server.server_port}/'
  if args.tune_test:logging.info('Operator RF tune-test service: %s',url)
  if args.read_only:logging.info('Read-only telemetry service: %s',url)
  if args.mode_test:logging.info('Restricted mode-test service: %s',url)
  if args.power_test:logging.info('Restricted power-test service: %s',url)
  if args.readiness_test:logging.info('Restricted readiness-test service: %s',url)
  webview.settings.update(ALLOW_FILE_URLS=False,ALLOW_DOWNLOADS=False,OPEN_EXTERNAL_LINKS_IN_BROWSER=False,OPEN_DEVTOOLS_IN_DEBUG=False)
  window=webview.create_window('OM Power Control · '+('OPERATOR RF TUNE TEST' if args.tune_test else 'NO-RF READINESS TEST' if args.readiness_test else 'POWER-CYCLE TEST' if args.power_test else 'OPERATE / STANDBY TEST' if args.mode_test else 'READ-ONLY TELEMETRY' if args.read_only else 'SIMULATION' if simulated else 'Hardware'),url,js_api=bridge,width=size[0],height=size[1],min_size=(380,620),on_top=preferences.get('alwaysOnTop',False),background_color='#111619',text_select=True)
  bridge._window=window
  def dispatch_display(options):
   from System import Action
   # pywebview 6.2.1 sets TopMost directly; WinForms requires its UI thread.
   window.native.BeginInvoke(Action(lambda:bridge._apply(options)))
  bridge._dispatch=dispatch_display
  def restrict_navigation():
   # WebView2 event runs on the UI thread. Permit only this session's UI.
   def navigating(sender,event):
    if str(event.Uri)!=url:event.Cancel=True
   window.native.webview.NavigationStarting+=navigating
  window.events.before_show+=restrict_navigation
  def remember_size():
   if not preferences.get('compact'):preferences['full_size']=[window.width,window.height]
   # Closing runs on the UI thread: do not wait for JS bridge work here.
   (directory/'window.json').write_text(json.dumps(preferences))
  window.events.closing+=remember_size
  failures=[]
  if args.smoke_test:
   import faulthandler
   trace=(directory/'smoke-trace.log').open('w')
   faulthandler.dump_traceback_later(20,file=trace)
  def smoke():
   if not args.smoke_test:return
   try:
    if not window.events.loaded.wait(25):raise RuntimeError('WebView2 did not load')
    import time
    deadline=time.monotonic()+10
    while window.evaluate_js("document.getElementById('status').textContent")!='Standby':
     if time.monotonic()>deadline:raise RuntimeError('Simulated telemetry did not render')
     time.sleep(.2)
    window.evaluate_js("document.getElementById('view').click()")
    time.sleep(.5)
    if not window.evaluate_js("document.body.classList.contains('compact')"):raise RuntimeError('Compact view failed')
    window.evaluate_js("document.getElementById('view').click()")
    window.evaluate_js("document.getElementById('onTop').click()")
    time.sleep(.5)
    if not window.on_top:raise RuntimeError('Stay on top bridge failed')
    window.evaluate_js("document.getElementById('onTop').click()")
    def wait_ui(expression):
     deadline=time.monotonic()+10
     while not window.evaluate_js(expression):
      if time.monotonic()>deadline:raise RuntimeError('UI condition timed out: '+expression)
      time.sleep(.1)
    window.evaluate_js("document.getElementById('toggle').click()")
    wait_ui("document.getElementById('status').textContent === 'Operate'")
    time.sleep(2.2)
    # Confirmation is accepted only in this explicitly offline smoke test.
    window.evaluate_js("window.confirm=()=>true; document.getElementById('autotuneStart').click()")
    wait_ui("lastState.autotune_phase === 'waiting'")
    window.evaluate_js("document.getElementById('simRFOn').click()")
    wait_ui("lastState.autotune_phase === 'succeeded' && lastState.autotune_saved === true")
    if not monitor.simulator.rf:raise RuntimeError('Simulated completion unexpectedly stopped operator RF')
    window.evaluate_js("document.getElementById('simRFOff').click()")
    wait_ui("lastState.transmitting === false")
    window.evaluate_js("document.getElementById('autotuneDismiss').click()")
    if not window.evaluate_js("document.getElementById('autotuneBanner').hidden"):raise RuntimeError('Dismiss failed')
    window.evaluate_js("document.getElementById('disconnect').click()")
    wait_ui("lastState.connection === 'Disconnected'")
    if window.evaluate_js("document.getElementById('forward').textContent")!='\u2014':raise RuntimeError('Unavailable-reading dash was decoded incorrectly')
    if window.evaluate_js("document.getElementById('temperature').textContent")!='\u2014 \u00b0C':raise RuntimeError('Temperature symbols were decoded incorrectly')
    logging.info('OFFLINE WEBVIEW2 SMOKE TEST PASSED')
   except Exception as exc:failures.append(exc);logging.exception('Smoke test failed')
   finally:window.destroy()
  webview.start(smoke,gui='edgechromium',private_mode=True,storage_path=str(directory/'WebView2'))
  if args.smoke_test:faulthandler.cancel_dump_traceback_later();trace.close()
  if failures:raise RuntimeError(str(failures[0]))
  return 0
 finally:
  if monitor:
   monitor.disconnect()
   if monitor.thread:monitor.thread.join(4)
  if feed:feed.shutdown();feed.server_close()
  if server:
   if worker and worker.is_alive():server.shutdown();worker.join(3)
   server.server_close()
  lock.close()
  if wire_trace_writer is not None:wire_trace_writer.close()

if __name__=='__main__':
 try:sys.exit(main())
 except Exception as exc:
  logging.exception('Windows host failed')
  if sys.stdout is not None:print(str(exc),file=sys.stderr)
  else:
   import ctypes
   ctypes.windll.user32.MessageBoxW(None,str(exc)+'\n\nSee %LOCALAPPDATA%\\OM Power Control\\windows.log','OM Power Control',0x10)
  sys.exit(1)

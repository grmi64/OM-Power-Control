"""Windows WebView2 host for the shared OM Power Control interface."""
import argparse,json,os,sys,threading,logging
from pathlib import Path
import settings
from instance_lock import InstanceLock,READER_MUTEX
from live import Monitor,create_server
from windows_runtime import ensure_webview2_runtime
from windows_dpi import configure_process_dpi,window_dpi,DpiWindowHook
from windows_access import prepare_launch,launch_replacement

def show_startup_error(exc):
 # A packaged windowed app can inherit redirected console handles from a
 # launcher. Always show its error to the operator, not only in hidden output.
 if getattr(sys,'frozen',False) or sys.stdout is None:
  import ctypes
  ctypes.windll.user32.MessageBoxW(None,str(exc)+'\n\nSee %LOCALAPPDATA%\\OM Power Control\\windows.log','OM Power Control',0x10|0x10000)
 elif sys.stderr is not None:print(str(exc),file=sys.stderr)

def load_preferences(path):
 try:
  value=json.loads(Path(path).read_text())
  if not isinstance(value,dict):return {}
  return {k:v for k,v in value.items() if k in ('compact','alwaysOnTop') and type(v) is bool or k=='full_size' and isinstance(v,list) and len(v)==2 and all(type(n) is int for n in v) and 380<=v[0]<=4000 and 200<=v[1]<=4000}
 except (OSError,ValueError):return {}

def visible_window_bounds(bounds,work_area):
 """Fit physical window bounds to the current monitor's physical work area."""
 x,y,width,height=bounds;left,top,available_width,available_height=work_area
 width=max(1,min(width,available_width));height=max(1,min(height,available_height))
 return (max(left,min(x,left+available_width-width)),max(top,min(y,top+available_height-height)),width,height)

def keep_window_visible(window,suggested=None):
 # Called only on the WinForms UI thread. Use one coordinate system for both
 # rectangles; CSS/pywebview logical dimensions differ at high DPI.
 from System.Drawing import Rectangle,Size
 from System.Windows.Forms import Screen,FormWindowState
 form=window.native
 area=(Screen.FromRectangle(Rectangle(*suggested)) if suggested else Screen.FromControl(form)).WorkingArea
 # WinForms DeviceDpi can stay at 96 under pythonnet even on a scaled screen.
 # The HWND reports the DPI actually used by pywebview's physical sizing.
 scale=window_dpi(form.Handle.ToInt64())/96
 form.MinimumSize=Size(min(round(380*scale),area.Width),min(round(620*scale),area.Height))
 if form.WindowState!=FormWindowState.Normal:return
 bounds=form.Bounds
 fitted=visible_window_bounds(suggested or (bounds.X,bounds.Y,bounds.Width,bounds.Height),(area.X,area.Y,area.Width,area.Height))
 if fitted!=(bounds.X,bounds.Y,bounds.Width,bounds.Height):form.Bounds=Rectangle(*fitted)

class DisplayBridge:
 def __init__(self,path,preferences):
  self._path=Path(path);self._preferences=preferences;self._window=None;self._lock=threading.Lock()
 def display_window(self,options):
  if not isinstance(options,dict) or any(type(options.get(k)) is not bool for k in ('compact','alwaysOnTop')):raise ValueError('Invalid window preferences')
  dispatch=getattr(self,'_dispatch',None)
  if dispatch:dispatch(dict(options))
  else:self._apply(options)
 def request_access_mode(self,value):
  if not getattr(self,'_access_allowed',False):raise ValueError('Mode changes are unavailable in this restricted test session')
  if getattr(self,'_access_args',None) is not None:raise ValueError('A mode change is already in progress')
  args=prepare_launch(value,self._monitor.snapshot())
  if getattr(self,'_access_smoke_only',False):
   if value['mode']!='simulation':raise ValueError('Offline access smoke permits simulation only')
   args.append('--smoke-test')
  self._access_args=args
  return {'reopening':True}
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

def _run_once(argv=None):
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
 parser.add_argument('--start-disconnected',action='store_true',help='Ignore auto-connect and wait for an explicit Connect click')
 parser.add_argument('--access-smoke-test',action='store_true',help='Offline simulation-only UI and self-relaunch test')
 parser.add_argument('--trace-telemetry',action='store_true',help='Save private bounded raw amplifier replies and decoder events under local application data')
 args=parser.parse_args(argv)
 if sys.platform!='win32':parser.error('The Windows desktop host requires Windows')
 if (args.smoke_test or args.access_smoke_test) and (args.hardware or args.read_only or args.mode_test or args.power_test or args.readiness_test or args.tune_test):parser.error('Smoke tests must be offline')
 if (args.host or args.amp_port is not None) and not (args.hardware or args.read_only or args.mode_test or args.power_test or args.readiness_test or args.tune_test):parser.error('An amplifier endpoint requires an explicit hardware access mode')
 configure_process_dpi()
 directory=settings.data_directory();directory.mkdir(parents=True,exist_ok=True)
 logging.basicConfig(filename=directory/'windows.log',level=logging.INFO)
 try:lock=InstanceLock(directory/'instance.lock',name=READER_MUTEX)
 except RuntimeError as exc:
  import ctypes
  ctypes.windll.user32.MessageBoxW(None,str(exc),'OM Power Control',0x40);return 1
 server=feed=None;worker=None;monitor=None;wire_trace_writer=None
 try:
  import webview
  runtime_version=ensure_webview2_runtime(Path(webview.__file__).parent)
  logging.info('WebView2 runtime available: %s',runtime_version)
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
  if not args.start_disconnected and (simulated or monitor.settings['auto_connect'] or ((args.read_only or args.mode_test or args.power_test or args.readiness_test or args.tune_test) and monitor.settings['host'])):monitor.connect()
  bridge=DisplayBridge(directory/'window.json',preferences);bridge._simulated=simulated
  bridge._read_only=args.read_only
  bridge._mode_test=args.mode_test
  bridge._power_test=args.power_test
  bridge._readiness_test=args.readiness_test
  bridge._tune_test=args.tune_test
  bridge._monitor=monitor
  bridge._access_allowed=not (args.mode_test or args.power_test or args.readiness_test or args.tune_test or args.smoke_test)
  bridge._access_args=None
  bridge._access_smoke_only=args.access_smoke_test
  access_config={'allowed':bridge._access_allowed,'mode':'simulation' if simulated else 'read-only' if args.read_only else 'hardware','host':monitor.settings['host'],'port':monitor.settings['port']}
  access_html=Path(__file__).with_name('windows_access.html').read_text(encoding='utf-8').replace('__WINDOWS_ACCESS_SCRIPT__','window.omAccessMode='+json.dumps(access_config).replace('<','\\u003c')+';'+Path(__file__).with_name('windows_access.js').read_text(encoding='utf-8'))
  server.html=server.html.replace('</main>',access_html+'</main>')
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
   def apply():
    bridge._apply(options);keep_window_visible(window)
   window.native.BeginInvoke(Action(apply))
  bridge._dispatch=dispatch_display
  def restrict_navigation():
   # WebView2 event runs on the UI thread. Permit only this session's UI.
   def navigating(sender,event):
    if str(event.Uri)!=url:event.Cancel=True
   window.native.webview.NavigationStarting+=navigating
   # Let the bridge reply finish before JS requests close. Destroying here from
   # request_access_mode races pywebview's asynchronous return-value delivery.
   def close_requested(sender,event):
    if bridge._access_args is not None and str(sender.Source)==url:window.destroy()
   def attach_access_close(sender=None,event=None):
    if not getattr(window,'_access_close_attached',False) and window.native.webview.CoreWebView2 is not None:
     window.native.webview.CoreWebView2.WindowCloseRequested+=close_requested
     window._access_close_attached=True
   window._access_close_hook=close_requested
   window._access_init_hook=attach_access_close
   window.native.webview.CoreWebView2InitializationCompleted+=attach_access_close
   attach_access_close()
   from System import Action
   # pythonnet's WinForms DPI event can be disabled. Observe the native
   # notification, then update the minimum and apply its rectangle after
   # Windows/WinForms process the message. This callback runs on the UI thread.
   # Keep a strong reference to the callback until the native window is destroyed.
   window._dpi_hook=DpiWindowHook(window.native.Handle.ToInt64(),lambda suggested:keep_window_visible(window,suggested))
   keep_window_visible(window)
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
   if args.access_smoke_test:
    try:
     import time
     if not window.events.loaded.wait(25):raise RuntimeError('Access UI did not load')
     def wait_access(expression):
      deadline=time.monotonic()+15
      while not window.evaluate_js(expression):
       if time.monotonic()>deadline:raise RuntimeError('Access UI condition timed out: '+expression)
       time.sleep(.1)
     wait_access("typeof lastState !== 'undefined' && lastState.connection === 'Connected'")
     if not window.evaluate_js("document.getElementById('applyAccessMode').disabled"):raise RuntimeError('Connected mode switch was enabled')
     window.evaluate_js("document.getElementById('view').click()")
     if not window.evaluate_js("document.getElementById('accessModePanel').getBoundingClientRect().height > 0"):raise RuntimeError('Compact view hides access selector')
     window.evaluate_js("document.getElementById('view').click();document.getElementById('disconnect').click()")
     wait_access("lastState.connection === 'Disconnected' && !document.getElementById('applyAccessMode').disabled")
     for mode in ('read-only','hardware'):
      window.evaluate_js("window.confirm=()=>false;document.getElementById('accessMode').value="+json.dumps(mode)+";document.getElementById('accessMode').onchange();document.getElementById('applyAccessMode').click()")
      time.sleep(.2)
      if bridge._access_args is not None:raise RuntimeError('Canceled hardware choice requested a launch')
     window.evaluate_js("document.getElementById('accessMode').value='simulation';document.getElementById('accessMode').onchange();document.getElementById('applyAccessMode').click()")
     deadline=time.monotonic()+5
     while bridge._access_args is None:
      if time.monotonic()>deadline:raise RuntimeError('Native simulation handoff was not requested')
      time.sleep(.1)
     logging.info('OFFLINE ACCESS MODE HANDOFF REQUESTED')
    except Exception as exc:failures.append(exc);logging.exception('Access smoke failed');window.destroy()
    return
   if not args.smoke_test:return
   try:
    if not window.events.loaded.wait(25):raise RuntimeError('WebView2 did not load')
    if args.start_disconnected:
     if monitor.snapshot()['connection']!='Disconnected' or monitor.simulator.sent:raise RuntimeError('Relaunch connected automatically')
     logging.info('OFFLINE RELAUNCH STARTED DISCONNECTED')
     window.evaluate_js("document.getElementById('connect').click()")
    # Exercise the actual HWND, not WinForms' potentially stale DeviceDpi or
    # mocked APIs. This remains an explicitly offline smoke test.
    import ctypes
    from System import Action
    from System.Windows.Forms import Screen
    from windows_dpi import _Rect,WM_DPICHANGED
    native_done=threading.Event();native_errors=[]
    def native_dpi_check():
     try:
      form=window.native;handle=form.Handle.ToInt64()
      api=ctypes.WinDLL('user32',use_last_error=True)
      api.GetWindowDpiAwarenessContext.argtypes=[ctypes.c_void_p];api.GetWindowDpiAwarenessContext.restype=ctypes.c_void_p
      api.AreDpiAwarenessContextsEqual.argtypes=[ctypes.c_void_p,ctypes.c_void_p];api.AreDpiAwarenessContextsEqual.restype=ctypes.c_int
      if not api.AreDpiAwarenessContextsEqual(api.GetWindowDpiAwarenessContext(handle),-4):raise RuntimeError('Window is not PerMonitorV2 aware')
      dpi=window_dpi(handle);area=Screen.FromControl(form).WorkingArea
      expected=(min(round(380*dpi/96),area.Width),min(round(620*dpi/96),area.Height))
      if (form.MinimumSize.Width,form.MinimumSize.Height)!=expected:raise RuntimeError('Minimum size does not use actual HWND DPI')
      b=form.Bounds;rect=_Rect(b.X,b.Y,b.Right,b.Bottom)
      before=window._dpi_hook.notifications
      api.SendMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_void_p];api.SendMessageW.restype=ctypes.c_ssize_t
      api.SendMessageW(handle,WM_DPICHANGED,dpi|(dpi<<16),ctypes.byref(rect))
      if window._dpi_hook.notifications!=before+1 or window._dpi_hook.last_error:raise RuntimeError('Native DPI notification was not handled')
      logging.info('OFFLINE DPI CHECK PASSED: PerMonitorV2, HWND DPI %s, minimum %s, synthetic notification delivered',dpi,expected)
     except Exception as exc:native_errors.append(exc)
     finally:native_done.set()
    window.native.BeginInvoke(Action(native_dpi_check))
    if not native_done.wait(5):raise RuntimeError('Native DPI check timed out')
    if native_errors:raise native_errors[0]
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
  return bridge._access_args if bridge._access_args is not None else 0
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

def main(argv=None):
 # A simulation session's temporary settings override must not follow the new
 # process into hardware mode (or leak back into a source-hosted caller).
 original=os.environ.get('OM_SETTINGS_PATH')
 try:result=_run_once(argv)
 finally:
  if original is None:os.environ.pop('OM_SETTINGS_PATH',None)
  else:os.environ['OM_SETTINGS_PATH']=original
 if isinstance(result,list):
  launch_replacement(result)
  return 0
 return result

if __name__=='__main__':
 try:sys.exit(main())
 except Exception as exc:
  logging.exception('Windows host failed')
  show_startup_error(exc)
  sys.exit(1)

"""DPI setup and actual-window sizing, without loading native Windows APIs."""
import ctypes,types,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock,patch
from windows_dpi import configure_process_dpi,window_dpi,DpiWindowHook,WM_DPICHANGED,WM_NCDESTROY,_Rect
from windows_app import keep_window_visible

class DpiTests(unittest.TestCase):
 def api(self,changed=1,verified=1):
  api=Mock();api.SetProcessDpiAwarenessContext.return_value=changed
  api.GetThreadDpiAwarenessContext.return_value=123
  api.AreDpiAwarenessContextsEqual.return_value=verified
  return api
 def test_sets_and_verifies_per_monitor_v2(self):
  api=self.api()
  with patch('windows_dpi._user32',return_value=api):configure_process_dpi()
  api.SetProcessDpiAwarenessContext.assert_called_once_with(-4)
  api.AreDpiAwarenessContextsEqual.assert_called_once_with(123,-4)
 def test_accepts_verified_manifest_initialization(self):
  with patch('windows_dpi._user32',return_value=self.api(0,1)),patch('windows_dpi._last_error',return_value=5):configure_process_dpi()
 def test_rejects_system_awareness_and_unknown_setup_failure(self):
  for changed,verified,error in ((0,0,5),(0,1,87),(1,0,0)):
   with self.subTest(changed=changed,verified=verified),patch('windows_dpi._user32',return_value=self.api(changed,verified)),patch('windows_dpi._last_error',return_value=error):
    with self.assertRaisesRegex(RuntimeError,'PerMonitorV2'):configure_process_dpi()
 def test_dpi_setup_failure_precedes_lock_monitor_and_server(self):
  import windows_app
  with patch.object(windows_app.sys,'platform','win32'),patch('windows_app.configure_process_dpi',side_effect=RuntimeError('DPI setup failed')),patch('windows_app.InstanceLock') as lock,patch('windows_app.Monitor') as monitor,patch('windows_app.create_server') as server:
   with self.assertRaisesRegex(RuntimeError,'DPI setup failed'):windows_app.main(['--read-only','--host','192.0.2.1'])
   lock.assert_not_called();monitor.assert_not_called();server.assert_not_called()
 def test_reads_dpi_from_hwnd_and_rejects_invalid_handle(self):
  api=self.api();api.GetDpiForWindow.return_value=120
  with patch('windows_dpi._user32',return_value=api):self.assertEqual(window_dpi(456),120)
  api.GetDpiForWindow.assert_called_once_with(456)
  api.GetDpiForWindow.return_value=0
  with patch('windows_dpi._user32',return_value=api):
   with self.assertRaises(RuntimeError):window_dpi(456)
 def test_minimum_uses_hwnd_dpi_even_when_winforms_reports_96(self):
  rectangle=lambda x,y,w,h:types.SimpleNamespace(X=x,Y=y,Width=w,Height=h)
  size=lambda w,h:types.SimpleNamespace(Width=w,Height=h)
  form=types.SimpleNamespace(WindowState=0,DeviceDpi=96,Handle=Mock(),Bounds=rectangle(0,0,900,900))
  form.Handle.ToInt64.return_value=456
  area=rectangle(0,0,1920,1104)
  modules={'System.Drawing':types.SimpleNamespace(Rectangle=rectangle,Size=size),'System.Windows.Forms':types.SimpleNamespace(Screen=types.SimpleNamespace(FromControl=lambda form:types.SimpleNamespace(WorkingArea=area)),FormWindowState=types.SimpleNamespace(Normal=0))}
  with patch.dict('sys.modules',modules),patch('windows_app.window_dpi',return_value=120) as dpi:keep_window_visible(types.SimpleNamespace(native=form))
  dpi.assert_called_once_with(456)
  self.assertEqual((form.MinimumSize.Width,form.MinimumSize.Height),(475,775))
  with patch.dict('sys.modules',modules),patch('windows_app.window_dpi',return_value=192):keep_window_visible(types.SimpleNamespace(native=form))
  self.assertEqual((form.MinimumSize.Width,form.MinimumSize.Height),(760,1104))
 def test_manifest_declares_per_monitor_v2_and_as_invoker(self):
  manifest=ET.parse(Path(__file__).with_name('windows_app.manifest')).getroot()
  dpi=manifest.find('.//{http://schemas.microsoft.com/SMI/2016/WindowsSettings}dpiAwareness')
  self.assertEqual(dpi.text,'PerMonitorV2')
  level=manifest.find('.//{urn:schemas-microsoft-com:asm.v3}requestedExecutionLevel')
  self.assertEqual(level.attrib['level'],'asInvoker')
 def test_lower_dpi_minimum_is_applied_before_suggested_smaller_bounds(self):
  rectangle=lambda x,y,w,h:types.SimpleNamespace(X=x,Y=y,Width=w,Height=h)
  size=lambda w,h:types.SimpleNamespace(Width=w,Height=h)
  class Form:
   WindowState=0;DeviceDpi=96;Handle=Mock()
   MinimumSize=size(760,1104);_bounds=rectangle(0,0,840,1104)
   @property
   def Bounds(self):return self._bounds
   @Bounds.setter
   def Bounds(self,value):
    if value.Width<self.MinimumSize.Width:raise AssertionError('Old high-DPI minimum still active')
    self.applied_minimum=(self.MinimumSize.Width,self.MinimumSize.Height);self._bounds=value
  form=Form();form.Handle.ToInt64.return_value=456;area=rectangle(0,0,1920,1104)
  screen=types.SimpleNamespace(FromRectangle=lambda rect:types.SimpleNamespace(WorkingArea=area))
  modules={'System.Drawing':types.SimpleNamespace(Rectangle=rectangle,Size=size),'System.Windows.Forms':types.SimpleNamespace(Screen=screen,FormWindowState=types.SimpleNamespace(Normal=0))}
  with patch.dict('sys.modules',modules),patch('windows_app.window_dpi',return_value=120):keep_window_visible(types.SimpleNamespace(native=form),(200,40,525,900))
  self.assertEqual(form.applied_minimum,(475,775));self.assertEqual(form.Bounds.Width,525)

class NativeDpiHookTests(unittest.TestCase):
 def setUp(self):
  self.api=Mock();self.api.SetWindowSubclass.return_value=1;self.api.DefSubclassProc.return_value=123
  self.user=Mock();self.user.SetWindowPos.return_value=1;self.changed=Mock()
  self.patches=[patch('windows_dpi._comctl32',return_value=self.api),patch('windows_dpi._user32',return_value=self.user),patch('windows_dpi._callback',side_effect=lambda fn:fn)]
  for item in self.patches:item.start()
  self.addCleanup(lambda:[item.stop() for item in reversed(self.patches)])
  self.hook=DpiWindowHook(456,self.changed)
 def test_dpi_notification_delivers_suggested_bounds_to_ui(self):
  rect=_Rect(-900,40,-100,940)
  self.assertEqual(self.hook._message(456,WM_DPICHANGED,144|(144<<16),ctypes.addressof(rect),self.hook.identity,0),123)
  self.changed.assert_called_once_with((-900,40,800,900))
  self.assertEqual(self.hook.notifications,1);self.assertIsNone(self.hook.last_error)
  self.api.DefSubclassProc.assert_called_once()
 def test_unrelated_messages_are_forwarded_without_resize(self):
  self.assertEqual(self.hook._message(456,0x0005,0,0,self.hook.identity,0),123)
  self.user.SetWindowPos.assert_not_called();self.changed.assert_not_called()
 def test_callback_failure_is_logged_not_propagated_to_windows(self):
  self.changed.side_effect=RuntimeError('Disposed window')
  with self.assertLogs(level='ERROR'):self.assertEqual(self.hook._message(456,WM_DPICHANGED,0,0,self.hook.identity,0),123)
  self.assertEqual(self.hook.last_error,'Disposed window')
 def test_window_destruction_removes_subclass_once(self):
  self.hook._message(456,WM_NCDESTROY,0,0,self.hook.identity,0);self.hook.close()
  self.api.RemoveWindowSubclass.assert_called_once_with(456,self.hook.callback,self.hook.identity)
 def test_registration_failure_is_reported(self):
  self.api.SetWindowSubclass.return_value=0
  with self.assertRaises(RuntimeError):DpiWindowHook(456,self.changed)

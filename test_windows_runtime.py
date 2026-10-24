"""Runtime absence fails before a backend or hardware reader can start."""
import ctypes,tempfile,types,unittest
import io
from pathlib import Path
from unittest.mock import Mock,patch
from windows_runtime import ensure_webview2_runtime,WebView2Unavailable

class RuntimeTests(unittest.TestCase):
 def test_packaged_failure_shows_dialog_even_with_redirected_stdout(self):
  import windows_app
  user32=Mock()
  with patch.object(windows_app.sys,'frozen',True,create=True),patch.object(windows_app.sys,'stdout',io.StringIO()),patch.object(ctypes,'windll',types.SimpleNamespace(user32=user32),create=True):
   windows_app.show_startup_error(WebView2Unavailable('Missing WebView2'))
  user32.MessageBoxW.assert_called_once();self.assertIn('Missing WebView2',user32.MessageBoxW.call_args.args[1])
 def probe(self,result=0,version='156.0.0.0'):
  loader=Mock();buffer=ctypes.create_unicode_buffer(version) if version is not None else None
  def query(folder,pointer):
   self.assertIsNone(folder)
   pointer._obj.value=ctypes.addressof(buffer) if buffer is not None else None
   return result
  loader.GetAvailableCoreWebView2BrowserVersionString.side_effect=query
  return loader,buffer
 def test_installed_runtime_is_reported_and_native_memory_freed(self):
  loader,buffer=self.probe()
  with patch('windows_runtime._load_loader',return_value=loader),patch('windows_runtime._free_version') as free:
   self.assertEqual(ensure_webview2_runtime(Path('webview')),'156.0.0.0');free.assert_called_once()
 def test_missing_runtime_shows_actionable_guidance(self):
  loader,_=self.probe(-2147024894,None)
  with patch('windows_runtime._load_loader',return_value=loader),patch('windows_runtime._free_version') as free:
   with self.assertRaises(WebView2Unavailable) as caught:ensure_webview2_runtime(Path('webview'))
   self.assertIn('Install or repair',str(caught.exception));self.assertIn('No amplifier connection',str(caught.exception));free.assert_not_called()
 def test_null_version_is_not_treated_as_available(self):
  loader,_=self.probe(0,None)
  with patch('windows_runtime._load_loader',return_value=loader):
   with self.assertRaises(WebView2Unavailable):ensure_webview2_runtime(Path('webview'))
 def test_failed_query_still_frees_allocated_version(self):
  loader,buffer=self.probe(-1)
  with patch('windows_runtime._load_loader',return_value=loader),patch('windows_runtime._free_version') as free:
   with self.assertRaises(WebView2Unavailable):ensure_webview2_runtime(Path('webview'))
   free.assert_called_once()
 def test_missing_loader_explains_complete_zip_requirement(self):
  with patch('windows_runtime._load_loader',side_effect=OSError('Missing DLL')):
   with self.assertRaisesRegex(WebView2Unavailable,'Extract the entire'):ensure_webview2_runtime(Path('webview'))
 def test_unavailable_runtime_never_creates_monitor_or_server(self):
  import windows_app
  with tempfile.TemporaryDirectory() as directory,patch.object(windows_app.sys,'platform','win32'),patch('windows_app.settings.data_directory',return_value=Path(directory)),patch('windows_app.InstanceLock') as lock,patch('windows_app.logging.basicConfig'),patch.dict('sys.modules',{'webview':types.SimpleNamespace(__file__=str(Path(directory)/'webview/__init__.py'))}),patch('windows_app.ensure_webview2_runtime',side_effect=WebView2Unavailable('Missing runtime')),patch('windows_app.Monitor') as monitor,patch('windows_app.create_server') as server:
   with self.assertRaises(WebView2Unavailable):windows_app.main(['--read-only','--host','192.0.2.1'])
   monitor.assert_not_called();server.assert_not_called();lock.return_value.close.assert_called_once()

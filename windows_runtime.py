"""Windows WebView2 preflight. No networking, downloads or amplifier access."""
import ctypes,platform,struct
from pathlib import Path

class WebView2Unavailable(RuntimeError):
 pass

def _load_loader(path):return ctypes.WinDLL(str(path))
def _free_version(pointer):
 free=ctypes.OleDLL('ole32').CoTaskMemFree
 free.argtypes=[ctypes.c_void_p];free.restype=None;free(pointer)

def ensure_webview2_runtime(webview_root):
 arch='x86' if struct.calcsize('P')==4 else 'arm64' if platform.machine().lower() in ('arm64','aarch64') else 'x64'
 path=Path(webview_root)/'lib'/'runtimes'/('win-'+arch)/'native'/'WebView2Loader.dll'
 try:loader=_load_loader(path)
 except OSError as exc:
  raise WebView2Unavailable('The application files are incomplete or could not be loaded.\n\nExtract the entire OM Power Control ZIP, keeping the _internal folder beside the EXE, then try again.\n\nNo amplifier connection was started.') from exc
 query=loader.GetAvailableCoreWebView2BrowserVersionString
 query.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_void_p)];query.restype=ctypes.c_long
 version=ctypes.c_void_p()
 try:
  result=query(None,ctypes.byref(version))
  if result!=0 or not version.value:
   raise WebView2Unavailable('Microsoft Edge WebView2 Runtime is unavailable.\n\nInstall or repair the Microsoft Edge WebView2 Evergreen Runtime, then reopen OM Power Control.\n\nDownload on a computer with internet access if needed:\nhttps://developer.microsoft.com/microsoft-edge/webview2/\n\nNo amplifier connection was started.')
  return ctypes.wstring_at(version.value)
 finally:
  if version.value:_free_version(version)

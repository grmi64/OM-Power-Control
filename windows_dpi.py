"""Native Windows DPI setup, before any GUI or amplifier worker is created."""
import ctypes,logging

PER_MONITOR_V2=-4

def _user32():return ctypes.WinDLL('user32',use_last_error=True)
def _last_error():return ctypes.get_last_error()

def configure_process_dpi():
 api=_user32()
 api.SetProcessDpiAwarenessContext.argtypes=[ctypes.c_void_p]
 api.SetProcessDpiAwarenessContext.restype=ctypes.c_int
 api.GetThreadDpiAwarenessContext.argtypes=[]
 api.GetThreadDpiAwarenessContext.restype=ctypes.c_void_p
 api.AreDpiAwarenessContextsEqual.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
 api.AreDpiAwarenessContextsEqual.restype=ctypes.c_int
 changed=api.SetProcessDpiAwarenessContext(PER_MONITOR_V2)
 error=_last_error() if not changed else 0
 verified=api.AreDpiAwarenessContextsEqual(api.GetThreadDpiAwarenessContext(),PER_MONITOR_V2)
 # A manifest can configure the process before Python starts. Windows then
 # returns ACCESS_DENIED for another process-level setup call; verify it.
 if not verified or (not changed and error!=5):
  raise RuntimeError(f'Windows could not enable PerMonitorV2 display scaling (error {error}). Close the app and try again.')

def window_dpi(handle):
 api=_user32()
 api.GetDpiForWindow.argtypes=[ctypes.c_void_p]
 api.GetDpiForWindow.restype=ctypes.c_uint
 dpi=api.GetDpiForWindow(handle)
 if not dpi:raise RuntimeError('Windows could not read the window DPI.')
 return dpi

WM_DPICHANGED=0x02E0
WM_NCDESTROY=0x0082

class _Rect(ctypes.Structure):
 _fields_=[('left',ctypes.c_int32),('top',ctypes.c_int32),('right',ctypes.c_int32),('bottom',ctypes.c_int32)]

def _comctl32():return ctypes.WinDLL('comctl32',use_last_error=True)
def _callback(function):
 return ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t,ctypes.c_size_t,ctypes.c_size_t)(function)

class DpiWindowHook:
 """Observe native DPI messages even when WinForms' managed event is disabled."""
 def __init__(self,handle,changed):
  self.handle=handle;self.changed=changed;self.installed=False;self.identity=id(self);self.notifications=0;self.last_error=None
  self.api=_comctl32();self.callback=_callback(self._message)
  self.api.SetWindowSubclass.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t];self.api.SetWindowSubclass.restype=ctypes.c_int
  self.api.RemoveWindowSubclass.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];self.api.RemoveWindowSubclass.restype=ctypes.c_int
  self.api.DefSubclassProc.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t];self.api.DefSubclassProc.restype=ctypes.c_ssize_t
  if not self.api.SetWindowSubclass(handle,self.callback,self.identity,0):raise RuntimeError('Windows could not install the DPI-change handler.')
  self.installed=True
 def _message(self,handle,message,wparam,lparam,identity,data):
  suggested=None
  try:
   if message==WM_DPICHANGED and lparam:
    rect=ctypes.cast(lparam,ctypes.POINTER(_Rect)).contents
    suggested=(rect.left,rect.top,rect.right-rect.left,rect.bottom-rect.top)
   if message==WM_NCDESTROY:self.close()
  except Exception:logging.exception('DPI message inspection failed')
  result=self.api.DefSubclassProc(handle,message,wparam,lparam)
  if message==WM_DPICHANGED:
   self.notifications+=1
   try:
    # The UI callback updates its minimum before applying this rectangle;
    # otherwise an old high-DPI minimum can defeat a smaller suggested size.
    self.changed(suggested)
   except Exception as exc:self.last_error=str(exc);logging.exception('DPI-change handling failed')
  return result
 def close(self):
  if self.installed:
   self.api.RemoveWindowSubclass(self.handle,self.callback,self.identity);self.installed=False

"""Process lifetime lock; the file remains in place to avoid unlink races."""
import os
from pathlib import Path

READER_MUTEX='Local\\OMPowerControl.Reader.v1'

class InstanceLock:
 def __init__(self,path,name=None):
  self.file=None;self._mutex=None;self._kernel=None
  # A named Windows object is shared across launch contexts even if their
  # application-data folders are redirected or virtualized differently.
  if os.name=='nt' and name:
   import ctypes
   from ctypes import wintypes
   self._kernel=ctypes.WinDLL('kernel32',use_last_error=True)
   self._kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
   self._kernel.CreateMutexW.restype=wintypes.HANDLE
   self._kernel.CloseHandle.argtypes=[wintypes.HANDLE]
   self._kernel.CloseHandle.restype=wintypes.BOOL
   ctypes.set_last_error(0)
   self._mutex=self._kernel.CreateMutexW(None,False,name)
   error=ctypes.get_last_error()
   if not self._mutex:raise ctypes.WinError(error)
   if error==183:
    self.close();raise RuntimeError('Another OM Power Control instance is already running. Use the existing window.')
  try:
   path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
   self.file=path.open('a+b')
   if path.stat().st_size==0:self.file.write(b'0');self.file.flush()
   self.file.seek(0)
   try:
    if os.name=='nt':
     import msvcrt
     msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
    else:
     import fcntl
     fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except OSError:
    raise RuntimeError('Another OM Power Control instance is already running. Use the existing window.') from None
  except BaseException:
   self.close();raise
 def close(self):
  if self.file:self.file.close();self.file=None
  if self._mutex:self._kernel.CloseHandle(self._mutex);self._mutex=None
 def __enter__(self):return self
 def __exit__(self,*args):self.close()

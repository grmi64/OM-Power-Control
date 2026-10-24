"""Single reader across Windows launch contexts with different settings paths."""
import os,subprocess,sys,tempfile,unittest,uuid
from pathlib import Path
from instance_lock import InstanceLock

@unittest.skipUnless(os.name=='nt','Windows named-object guard')
class WindowsInstanceTests(unittest.TestCase):
 def test_different_data_directories_cannot_open_second_reader(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);name='Local\\OMPowerControl.Test.'+uuid.uuid4().hex
   command=[sys.executable,'-c','from instance_lock import InstanceLock; import sys; InstanceLock(sys.argv[1],name=sys.argv[2]).close()',str(root/'other'/'instance.lock'),name]
   with InstanceLock(root/'first'/'instance.lock',name=name):
    blocked=subprocess.run(command,capture_output=True)
    self.assertNotEqual(blocked.returncode,0);self.assertIn(b'already running',blocked.stderr)
   self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
 def test_guard_is_released_if_file_setup_fails(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);blocker=root/'file';blocker.write_text('not a directory')
   name='Local\\OMPowerControl.Test.'+uuid.uuid4().hex
   with self.assertRaises(OSError):InstanceLock(blocker/'instance.lock',name=name)
   with InstanceLock(root/'valid'/'instance.lock',name=name):pass

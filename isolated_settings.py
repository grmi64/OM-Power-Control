"""Import first in tests that build a Monitor: keeps them off the real settings file.

Monitor() loads the saved settings, so a developer's own saved model, address or
callsign would otherwise change test outcomes (an OM-4001A label blocks controls)."""
import atexit,os,shutil,tempfile
if 'OM_SETTINGS_PATH' not in os.environ:
    _directory=tempfile.mkdtemp(prefix='om-test-settings-');atexit.register(shutil.rmtree,_directory,True)
    os.environ['OM_SETTINGS_PATH']=os.path.join(_directory,'settings.json')

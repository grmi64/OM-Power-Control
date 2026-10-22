import unittest,tempfile,os
from pathlib import Path
from unittest.mock import patch
import settings
class Tests(unittest.TestCase):
 def test_roundtrip(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'OM_SETTINGS_PATH':str(Path(d)/'prefs.json')}):
   self.assertFalse(settings.load()['auto_connect']);v={**settings.DEFAULTS,'host':'192.0.2.1','callsign':'w1aw','auto_connect':True};settings.save(v);self.assertEqual(settings.load()['callsign'],'W1AW');self.assertTrue(settings.load()['auto_connect'])
 def test_station_changes_while_connected(self):
  from live import Monitor
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'OM_SETTINGS_PATH':str(Path(d)/'prefs.json')}):
   m=Monitor();m.settings['host']='192.0.2.1';m.thread=unittest.mock.Mock();m.thread.is_alive.return_value=True
   m.configure({**m.settings,'callsign':'w1aw','auto_connect':True})
   self.assertEqual(m.settings['callsign'],'W1AW');self.assertTrue(m.settings['auto_connect'])
   with self.assertRaises(ValueError):m.configure({**m.settings,'port':10002})
   with self.assertRaises(ValueError):m.configure({**m.settings,'host':'192.0.2.2'})
   self.assertEqual(m.settings['port'],10001)
 def test_new_install_has_no_station_address_or_auto_connect(self):
  from live import Monitor
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'OM_SETTINGS_PATH':str(Path(d)/'prefs.json')}):
   m=Monitor();self.assertEqual(m.settings['host'],'');self.assertEqual(m.settings['callsign'],'');self.assertFalse(m.settings['auto_connect'])
   with self.assertRaises(ValueError):m.connect()
   self.assertIsNone(m.thread)
 def test_model_migration_and_monitoring_only(self):
  from live import Monitor
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'OM_SETTINGS_PATH':str(Path(d)/'prefs.json')}):
   old={k:v for k,v in settings.DEFAULTS.items() if k!='model'}
   self.assertEqual(settings.validate(old)['model'],'OM-3501A')
   m=Monitor();m.configure({**m.settings,'model':'om-4001a'})
   self.assertEqual(settings.load()['model'],'OM-4001A')
   for action in ('toggle','on','off'):
    with self.assertRaisesRegex(ValueError,'Monitoring only'):m.command(action,'test-request-123')
   self.assertIsNone(m.controls.pending)
   m.thread=unittest.mock.Mock();m.thread.is_alive.return_value=True
   with self.assertRaises(ValueError):m.configure({**m.settings,'model':'OM-3501A'})
 def test_display_preference_persists_without_reconnecting(self):
  from live import Monitor
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'OM_SETTINGS_PATH':str(Path(d)/'prefs.json')}):
   m=Monitor();m.thread=unittest.mock.Mock();m.thread.is_alive.return_value=True
   for key in ('reflected','input','plate_a','gain_db'):
    m.configure_display({'secondary_measurement':key});self.assertEqual(settings.load()['secondary_measurement'],key)
    self.assertEqual(Monitor().settings['secondary_measurement'],key)
   self.assertEqual(m.settings['host'],'');self.assertIsNone(m.controls.pending)
   with self.assertRaises(ValueError):m.configure_display({'secondary_measurement':'bad'})
   with self.assertRaises(ValueError):m.configure_display({'secondary_measurement':'input','host':'192.0.2.2'})
 def test_invalid(self):
  for v in ({**settings.DEFAULTS,'port':0},{**settings.DEFAULTS,'host':'bad/host'},{**settings.DEFAULTS,'port':True}):
   with self.assertRaises(ValueError):settings.validate(v)
if __name__=='__main__':unittest.main()

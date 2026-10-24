"""Offline port acceptance tests. All amplifier socket creation is forbidden."""
import json,os,tempfile,threading,time,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch,Mock
from live import Monitor,create_server
from instance_lock import InstanceLock
from windows_app import DisplayBridge,load_preferences

class OfflinePortTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.env=patch.dict(os.environ,{'OM_SETTINGS_PATH':str(self.root/'settings.json')});self.env.start()
  # HTTP acceptance tests use loopback below; simulator tests forbid even that.
  self.network=patch('session_protocol.socket.create_connection',side_effect=AssertionError('No real amplifier connection permitted'))
  self.network.start();self.m=Monitor(simulate=True);self.m.connect()
  self.wait(lambda:self.m.snapshot()['connection']=='Connected')
 def tearDown(self):
  self.m.disconnect();self.m.thread.join(3);self.network.stop();self.env.stop();self.temp.cleanup()
 def wait(self,predicate,timeout=3):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   if predicate():return
   time.sleep(.02)
  self.fail('Timed out: '+str(self.m.snapshot()))
 def command(self,action):
  self.m.controls.last_sent-=3
  self.m.command(action,'offline-'+str(time.monotonic_ns()))
  self.wait(lambda:not self.m.snapshot()['control']['pending'])
 def ready(self):
  self.command('toggle');self.command('autotune')
  self.wait(lambda:self.m.snapshot().get('autotune_phase')=='waiting')
  self.assertFalse(self.m.simulator.rf,'Auto-tune must never create RF')
  self.assertEqual(self.m.simulator.sent.count(b'L'),1);self.assertEqual(self.m.simulator.sent.count(b'&'),1)
 def start_rf(self,scenario='success'):
  self.m.simulator.set_input(True,scenario)
  self.wait(lambda:self.m.snapshot().get('autotune_phase')=='tuning')
 def test_simulation_ignores_saved_address_and_autoconnect(self):
  self.assertEqual(self.m.settings['host'],'simulation');self.assertTrue(self.m.snapshot()['simulated'])
  m=Monitor();m.settings.update(host='192.0.2.1',auto_connect=True)
  with self.assertRaisesRegex(ValueError,'Hardware access is disabled'):m.connect()
  m.run();self.assertIn('Hardware access is disabled',m.snapshot()['error'])
 def test_tuning_success_requires_operator_rf_and_completion(self):
  self.ready();self.start_rf()
  self.assertNotEqual(self.m.snapshot().get('autotune_phase'),'succeeded')
  with self.m.simulator.lock:self.m.simulator.started-=5
  self.wait(lambda:self.m.snapshot().get('autotune_saved') is True)
  self.assertTrue(self.m.simulator.rf,'Completion must not control RF')
  with self.assertRaises(ValueError):self.m.command('off','blocked-rf-123')
  self.m.simulator.set_input(False);self.wait(lambda:not self.m.snapshot()['transmitting'])
  self.assertEqual(self.m.snapshot()['forward'],0)
 def test_stop_then_operator_rf_off_then_exit_is_not_success(self):
  self.ready();self.start_rf();self.command('autotune-stop')
  self.assertTrue(self.m.simulator.rf)
  with self.assertRaises(ValueError):self.m.command('autotune-exit','blocked-exit-123')
  self.m.simulator.set_input(False);self.wait(lambda:not self.m.snapshot()['transmitting'])
  self.command('autotune-exit');s=self.m.snapshot()
  self.assertEqual(s['autotune_phase'],'stopped-exited');self.assertFalse(s['autotune_saved'])
  self.assertEqual(self.m.simulator.sent.count(b'8'),1)
 def test_rf_release_restores_defaults_only_after_exit(self):
  self.ready();self.start_rf();self.m.simulator.set_input(False)
  self.wait(lambda:self.m.snapshot().get('autotune_phase')=='aborted')
  self.assertEqual(self.m.snapshot()['autotune_abort_origin'],'rf_lost')
  self.command('autotune-exit');self.assertEqual(self.m.snapshot()['autotune_phase'],'defaults')
  self.assertFalse(self.m.snapshot()['autotune_saved'])
 def test_waiting_exit(self):
  self.ready();self.command('autotune-exit');self.assertEqual(self.m.snapshot()['autotune_phase'],'cancelled')
 def test_unexpected_reply_never_counts_as_success(self):
  self.ready();self.start_rf('unexpected')
  with self.m.simulator.lock:self.m.simulator.started-=5
  self.wait(lambda:self.m.snapshot().get('autotune_phase')=='unknown')
  self.assertFalse(self.m.snapshot()['autotune_saved'])
  with self.assertRaises(ValueError):self.m.command('off','unknown-123')
 def test_lost_connection_never_reconnects_or_retries(self):
  self.ready();self.m.simulator.set_input(True,'disconnect')
  self.wait(lambda:self.m.snapshot()['connection']=='Disconnected')
  self.assertIsNone(self.m.snapshot()['forward']);self.assertEqual(self.m.simulator.sent.count(b'L'),1)
 def test_windows_preferences_and_native_bridge(self):
  p=self.root/'window.json';bridge=DisplayBridge(p,{})
  bridge._window=Mock(width=900,height=900);bridge._simulated=True
  bridge.display_window({'compact':True,'alwaysOnTop':True})
  bridge._window.resize.assert_called_once_with(420,790);self.assertTrue(bridge._window.on_top)
  bridge.display_window({'compact':False,'alwaysOnTop':False})
  self.assertEqual(load_preferences(p)['full_size'],[900,900]);self.assertFalse(bridge._window.on_top)
  with self.assertRaises(ValueError):bridge.display_window({'compact':'yes'})
  p.write_text('[]');self.assertEqual(load_preferences(p),{})
 def test_lock_blocks_second_process_and_releases(self):
  import subprocess,sys
  path=self.root/'instance.lock'
  command=[sys.executable,'-c','from instance_lock import InstanceLock; import sys; InstanceLock(sys.argv[1]).close()',str(path)]
  with InstanceLock(path):self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
  self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)

class LocalHTTPTests(unittest.TestCase):
 def test_ui_assets_ignore_windows_legacy_text_encoding(self):
  original=Path.read_text
  def legacy_default(path,*args,**kwargs):
   kwargs.setdefault('encoding','cp1252')
   return original(path,*args,**kwargs)
  with patch.object(Path,'read_text',legacy_default):
   server=create_server(Monitor(simulate=True))
  try:
   self.assertIn('id="forward">\u2014</span>',server.html)
   self.assertIn('\u00b0C',server.html)
   self.assertIn('REFLECTED \u00b7 W',server.html)
   self.assertNotIn('\u00e2\u20ac',server.html)
   self.assertNotIn('\u00c2\u00b0',server.html)
  finally:server.server_close()
 def test_token_required_and_simulation_route_cannot_enable_hardware(self):
  # Only numeric loopback HTTP; Monitor.connect remains gated.
  monitor=Monitor(simulate=True);server=create_server(monitor)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  base=f'http://127.0.0.1:{server.server_port}'
  def post(token,value):
   req=urllib.request.Request(base+'/simulation',json.dumps(value).encode(),headers={'X-OM-Token':token,'Content-Type':'application/json'})
   return urllib.request.urlopen(req,timeout=3)
  try:
   with urllib.request.urlopen(base) as response:
    html=response.read().decode();self.assertNotIn('__NATIVE_PREFERENCES__',html);self.assertIn(server.token,html)
   with self.assertRaises(urllib.error.HTTPError) as exc:post('bad',{'rf':True})
   self.assertEqual(exc.exception.code,403)
   with post(server.token,{'rf':True}):pass
   self.assertTrue(monitor.simulator.rf)
   monitor.simulate=False
   with self.assertRaises(urllib.error.HTTPError) as exc:post(server.token,{'rf':False})
   self.assertEqual(exc.exception.code,409)
  finally:server.shutdown();server.server_close();thread.join(2)

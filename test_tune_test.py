"""Operator RF-tune scope is tested entirely offline, including forbidden writes."""
import os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from live import Monitor
from session_protocol import TuneTestSocket,ReadOnlySocket
from test_session_protocol import Socket

class TuneTestTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'OM_SETTINGS_PATH':str(Path(self.temp.name)/'settings.json')});self.env.start()
 def tearDown(self):self.env.stop();self.temp.cleanup()
 def test_wire_blocks_power_unknown_combined_repeats_and_wrong_order(self):
  wire=Socket([]);counts={};sock=TuneTestSocket(wire,counts=counts)
  for data in (b'Y',b'Z',b'OL',b'',b'L',b'&',b'8',b'*'):
   with self.assertRaises(ValueError):sock.sendall(data)
  for data in (b'O',b'L',b'&',b'8',b'*',b'O'):sock.sendall(data)
  for data in TuneTestSocket.LIMITS:
   with self.assertRaises(ValueError):sock.sendall(data)
  for data in ReadOnlySocket.ALLOWED:sock.sendall(data)
  self.assertNotIn(b'Y',wire.sent);self.assertNotIn(b'Z',wire.sent)
 def test_backend_blocks_power_shared_controls_and_out_of_order_mode(self):
  m=Monitor(simulate=True,tune_test=True)
  m.state={'connection':'Connected','status':'Standby','transmitting':False,'_received':time.monotonic()}
  for action in ('on','off','autotune','autotune-stop','autotune-exit'):
   with self.assertRaises(ValueError):m.command(action,'blocked-'+action)
  with self.assertRaises(ValueError):m.command('toggle','shared-123',expected_mode='Standby',source='DXC')
  with self.assertRaises(ValueError):m.command('toggle','wrong-mode-123',expected_mode='Operate')
  self.assertIsNone(m.controls.pending)
 def test_mutually_exclusive_and_reconnect_never_resets_budget(self):
  for policy in ('read_only','mode_test','power_test','readiness_test'):
   with self.assertRaises(ValueError):Monitor(tune_test=True,**{policy:True})
  m=Monitor(simulate=True,tune_test=True);m.tune_test_counts[b'O']=1
  with self.assertRaises(ValueError):m.connect()
 def wait(self,condition):
  deadline=time.monotonic()+4
  while not condition():
   self.assertLess(time.monotonic(),deadline);time.sleep(.02)
 def command(self,m,action,key,expected=None):
  m.controls.last_sent-=3;m.command(action,key,expected_mode=expected);self.wait(lambda:not m.controls.pending)
 def test_one_successful_operator_tune_then_standby_no_power(self):
  with patch('session_protocol.socket.create_connection',side_effect=AssertionError('Offline only')):
   m=Monitor(simulate=True,tune_test=True);m.connect()
   try:
    self.wait(lambda:m.snapshot()['connection']=='Connected')
    self.command(m,'toggle','operator-mode-123','Standby')
    self.command(m,'autotune','operator-tune-123')
    self.assertEqual(m.snapshot()['autotune_phase'],'waiting');self.assertFalse(m.simulator.rf)
    m.simulator.set_input(True);self.wait(lambda:m.snapshot().get('autotune_phase')=='tuning')
    with m.simulator.lock:m.simulator.started-=5
    self.wait(lambda:m.snapshot().get('autotune_saved') is True)
    self.assertTrue(m.simulator.rf,'App must not stop operator RF')
    with self.assertRaises(ValueError):m.command('toggle','rf-blocked-123',expected_mode='Operate')
    m.simulator.set_input(False);self.wait(lambda:not m.snapshot()['transmitting'])
    self.command(m,'toggle','operator-standby-123','Operate')
    self.assertEqual(m.snapshot()['status'],'Standby')
    self.assertEqual([x for x in m.simulator.sent if x not in ReadOnlySocket.ALLOWED],[b'O',b'L',b'&',b'O'])
    with self.assertRaises(ValueError):m.command('toggle','extra-mode-123',expected_mode='Standby')
    self.assertEqual(m.snapshot()['tune_test_counts'],{'O':2,'L':1,'&':1})
   finally:m.disconnect();m.thread.join(3)
 def test_injected_power_command_is_blocked_before_socket_write(self):
  with patch('session_protocol.socket.create_connection',side_effect=AssertionError('Offline only')):
   m=Monitor(simulate=True,tune_test=True)
   with patch.object(m.controls,'take',return_value=b'Y'):m.run()
   self.assertIn('blocks power',m.snapshot()['error']);self.assertNotIn(b'Y',m.simulator.sent)

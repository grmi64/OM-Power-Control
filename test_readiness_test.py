"""No-RF acceptance scope: Operate, readiness, Exit, then Standby once."""
import time,unittest
from unittest.mock import patch
from controls import COMMANDS
from live import Monitor
from session_protocol import ReadinessTestSocket,ReadOnlySocket
from test_session_protocol import Socket

class ReadinessTests(unittest.TestCase):
 def test_wire_allows_only_exact_sequence_and_blocks_power_and_repeats(self):
  wire=Socket([]);sock=ReadinessTestSocket(wire)
  for wanted in ReadinessTestSocket.SEQUENCE:
   for data in (b'Y',b'Z',b'8',b'OL',b'',b'L',b'&',b'*',b'O'):
    if data!=wanted:
     with self.assertRaises(ValueError):sock.sendall(data)
   for poll in ReadOnlySocket.ALLOWED:sock.sendall(poll)
   sock.sendall(wanted)
  for data in ReadinessTestSocket.SEQUENCE:
   with self.assertRaises(ValueError):sock.sendall(data)
  self.assertEqual([v for v in wire.sent if v not in ReadOnlySocket.ALLOWED],list(ReadinessTestSocket.SEQUENCE))
 def test_backend_blocks_power_stop_shared_controls_and_wrong_steps(self):
  monitor=Monitor(simulate=True,readiness_test=True)
  monitor.state={'connection':'Connected','status':'Standby','_received':time.monotonic(),'transmitting':False}
  for action in COMMANDS:
   if action!='toggle':
    with self.assertRaises(ValueError):monitor.command(action,'blocked-'+action)
  with self.assertRaises(ValueError):monitor.command('toggle','wrong-mode-123',expected_mode='Operate')
  with self.assertRaises(ValueError):monitor.command('toggle','shared-123',expected_mode='Standby',source='DXC')
  self.assertIsNone(monitor.controls.pending)
 def test_complete_worker_sequence_uses_no_rf_and_never_claims_success(self):
  with patch('session_protocol.socket.create_connection',side_effect=AssertionError('Offline only')):
   monitor=Monitor(simulate=True,readiness_test=True);monitor.connect()
   def wait(condition):
    deadline=time.monotonic()+3
    while not condition():
     self.assertLess(time.monotonic(),deadline);time.sleep(.02)
   def command(action,key,expected=None):
    monitor.controls.last_sent-=3;monitor.command(action,key,expected_mode=expected)
    wait(lambda:not monitor.controls.pending)
   try:
    wait(lambda:monitor.snapshot()['connection']=='Connected')
    command('toggle','ready-operate-123','Standby')
    command('autotune','ready-autotune-123')
    self.assertEqual(monitor.snapshot()['autotune_phase'],'waiting');self.assertFalse(monitor.simulator.rf)
    self.assertEqual(monitor.readiness_test_sent,3)
    monitor.command('autotune','ready-autotune-123')
    with self.assertRaises(ValueError):monitor.command('toggle','early-standby-123',expected_mode='Operate')
    command('autotune-exit','ready-exit-123')
    self.assertEqual(monitor.snapshot()['autotune_phase'],'cancelled');self.assertFalse(monitor.snapshot()['autotune_saved'])
    command('toggle','ready-standby-123','Operate')
    self.assertEqual(monitor.snapshot()['status'],'Standby');self.assertFalse(monitor.simulator.rf)
    self.assertEqual([v for v in monitor.simulator.sent if v not in ReadOnlySocket.ALLOWED],list(ReadinessTestSocket.SEQUENCE))
    self.assertEqual(len([h for h in monitor.command_history if h['phase']=='confirmed']),4)
    with self.assertRaises(ValueError):monitor.command('toggle','extra-mode-123',expected_mode='Standby')
   finally:monitor.disconnect();monitor.thread.join(3)
   with self.assertRaises(ValueError):monitor.connect()
 def test_unexpected_entry_ack_does_not_arm_or_retry(self):
  with patch('session_protocol.socket.create_connection',side_effect=AssertionError('Offline only')):
   monitor=Monitor(simulate=True,readiness_test=True);monitor.connect()
   def wait(condition):
    deadline=time.monotonic()+3
    while not condition():
     self.assertLess(time.monotonic(),deadline);time.sleep(.02)
   try:
    wait(lambda:monitor.snapshot()['connection']=='Connected')
    monitor.command('toggle','unknown-operate-123',expected_mode='Standby');wait(lambda:not monitor.controls.pending)
    original=monitor.simulator.sendall
    def unexpected(data):
     if data==b'L':
      with monitor.simulator.lock:monitor.simulator.sent.append(data);monitor.simulator.emit(b'AUTO:UNEXPECTED;')
     else:original(data)
    monitor.simulator.sendall=unexpected;monitor.controls.last_sent-=3
    monitor.command('autotune','unknown-tune-123');wait(lambda:monitor.controls.uncertain)
    self.assertNotIn(b'&',monitor.simulator.sent);self.assertEqual(monitor.simulator.sent.count(b'L'),1)
   finally:monitor.disconnect();monitor.thread.join(3)
 def test_rf_or_stale_data_blocks_the_first_command(self):
  for transmitting,age in ((True,0),(False,4)):
   monitor=Monitor(simulate=True,readiness_test=True)
   monitor.state={'connection':'Connected','status':'Standby','_received':time.monotonic()-age,'transmitting':transmitting}
   with self.assertRaises(ValueError):monitor.command('toggle','no-rf-123',expected_mode='Standby')
   self.assertEqual(monitor.readiness_test_sent,0)
 def test_rf_blocks_waiting_exit(self):
  monitor=Monitor(simulate=True,readiness_test=True);monitor.readiness_test_sent=3
  monitor.state={'connection':'Connected','status':'Operate','autotune_phase':'waiting','_received':time.monotonic(),'transmitting':True}
  with self.assertRaises(ValueError):monitor.command('autotune-exit','rf-exit-123')
 def test_policies_cannot_be_combined(self):
  for other in ('read_only','mode_test','power_test'):
   with self.assertRaises(ValueError):Monitor(readiness_test=True,**{other:True})

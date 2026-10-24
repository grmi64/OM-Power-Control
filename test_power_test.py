"""Offline checks for an explicitly authorized shutdown/warm-up cycle."""
import time,unittest
from unittest.mock import patch
from controls import COMMANDS
from live import Monitor
from session_protocol import PowerCycleTestSocket,ReadOnlySocket
from test_session_protocol import Socket

class PowerCycleTests(unittest.TestCase):
 def test_wire_requires_shutdown_then_power_on_and_blocks_all_other_controls(self):
  wire=Socket([]);sock=PowerCycleTestSocket(wire)
  for data in [b'Y',b'O',b'L',b'&',b'8',b'*',b'ZZ',b'ZY',b'']:
   with self.assertRaises(ValueError):sock.sendall(data)
  sock.sendall(b'Z')
  with self.assertRaises(ValueError):sock.sendall(b'Z')
  for data in ReadOnlySocket.ALLOWED:sock.sendall(data)
  sock.sendall(b'Y')
  for data in (b'Y',b'Z',b'O',b'L'):
   with self.assertRaises(ValueError):sock.sendall(data)
  self.assertEqual([v for v in wire.sent if v not in ReadOnlySocket.ALLOWED],[b'Z',b'Y'])
 def test_backend_blocks_operate_tuning_wrong_order_and_shared_controls(self):
  monitor=Monitor(simulate=True,power_test=True)
  monitor.state={'connection':'Connected','status':'Standby','_received':time.monotonic(),'transmitting':False}
  for action in COMMANDS:
   if action!='off':
    with self.assertRaises(ValueError):monitor.command(action,'blocked-'+action)
  with self.assertRaises(ValueError):monitor.command('off','shared-off-123',source='DXC')
  self.assertIsNone(monitor.controls.pending)
 def test_full_cooling_off_warmup_standby_sequence_without_retries(self):
  with patch('session_protocol.socket.create_connection',side_effect=AssertionError('Offline only')):
   monitor=Monitor(simulate=True,power_test=True);monitor.connect()
   def wait(condition):
    deadline=time.monotonic()+5
    while not condition():
     self.assertLess(time.monotonic(),deadline);time.sleep(.02)
   try:
    wait(lambda:monitor.snapshot()['connection']=='Connected')
    monitor.command('off','power-cycle-off')
    wait(lambda:monitor.snapshot().get('status')=='Cooling down' and not monitor.controls.pending)
    monitor.command('off','power-cycle-off')
    with self.assertRaises(ValueError):monitor.command('on','too-early-on')
    self.assertEqual(monitor.simulator.sent.count(b'Z'),1)
    wait(lambda:monitor.snapshot().get('status')=='Off')
    monitor.command('on','power-cycle-on')
    wait(lambda:monitor.snapshot().get('status')=='Warming up' and not monitor.controls.pending)
    for action in COMMANDS:
     with self.assertRaises(ValueError):monitor.command(action,'extra-'+action)
    wait(lambda:monitor.snapshot().get('status')=='Standby')
    self.assertFalse(monitor.snapshot()['transmitting'])
    self.assertEqual(monitor.power_test_sent,2)
    self.assertEqual([v for v in monitor.simulator.sent if v not in ReadOnlySocket.ALLOWED],[b'Z',b'Y'])
    self.assertEqual(len([h for h in monitor.command_history if h['phase']=='confirmed']),2)
   finally:monitor.disconnect();monitor.thread.join(3)
   with self.assertRaises(ValueError):monitor.connect()
 def test_rf_and_stale_data_block_shutdown(self):
  for transmitting,age in ((True,0),(False,4)):
   monitor=Monitor(simulate=True,power_test=True)
   monitor.state={'connection':'Connected','status':'Standby','_received':time.monotonic()-age,'transmitting':transmitting}
   with self.assertRaises(ValueError):monitor.command('off','guarded-off-123')
   self.assertEqual(monitor.power_test_sent,0)
 def test_policies_cannot_be_combined(self):
  for other in ('read_only','mode_test'):
   with self.assertRaises(ValueError):Monitor(power_test=True,**{other:True})
 def test_injected_mode_command_never_reaches_the_socket(self):
  with patch('session_protocol.socket.create_connection',side_effect=AssertionError('Offline only')):
   monitor=Monitor(simulate=True,power_test=True);monitor.connect()
   deadline=time.monotonic()+3
   while monitor.snapshot()['connection']!='Connected':
    self.assertLess(time.monotonic(),deadline);time.sleep(.02)
   with monitor.lock:monitor.controls.pending={'action':'toggle','id':'injected-operate','sent':None,'expected_mode':'Standby'}
   monitor.thread.join(3)
   self.assertFalse(monitor.thread.is_alive());self.assertNotIn(b'O',monitor.simulator.sent)
   self.assertTrue(set(monitor.simulator.sent)<=ReadOnlySocket.ALLOWED)

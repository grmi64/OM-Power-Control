"""Offline validation for one explicitly authorized Operate -> Standby pair."""
import time,unittest
from unittest.mock import patch
from controls import COMMANDS
from live import Monitor
from session_protocol import ModeTestSocket,ReadOnlySocket
from test_session_protocol import Socket

class ModeTestTests(unittest.TestCase):
 def test_wire_allows_only_telemetry_and_two_mode_bytes(self):
  wire=Socket([]);sock=ModeTestSocket(wire)
  for data in ReadOnlySocket.ALLOWED:sock.sendall(data)
  for data in [v[0] for name,v in COMMANDS.items() if name!='toggle']+[b'&',b'OO',b'']:
   with self.assertRaises(ValueError):sock.sendall(data)
  sock.sendall(b'O');sock.sendall(b'O')
  with self.assertRaises(ValueError):sock.sendall(b'O')
  self.assertEqual(wire.sent.count(b'O'),2)
  self.assertTrue(set(wire.sent)<=(ReadOnlySocket.ALLOWED|{b'O'}))
 def test_backend_rejects_other_commands_and_wrong_order(self):
  monitor=Monitor(simulate=True,mode_test=True)
  monitor.state={'connection':'Connected','status':'Standby','_received':time.monotonic(),'transmitting':False}
  for action in COMMANDS:
   if action!='toggle':
    with self.assertRaises(ValueError):monitor.command(action,'forbidden-'+action)
  for expected in (None,'Operate'):
   with self.assertRaises(ValueError):monitor.command('toggle','wrong-order-123',expected_mode=expected)
  with self.assertRaises(ValueError):monitor.command('toggle','shared-123',expected_mode='Standby',source='DXC')
  self.assertIsNone(monitor.controls.pending)
 def test_monitor_executes_pair_once_and_exhausts_budget(self):
  with patch('session_protocol.socket.create_connection',side_effect=AssertionError('Offline test must not open amplifier sockets')):
   monitor=Monitor(simulate=True,mode_test=True);monitor.connect()
   def wait(condition):
    deadline=time.monotonic()+3
    while not condition():
     self.assertLess(time.monotonic(),deadline);time.sleep(.02)
   try:
    wait(lambda:monitor.snapshot()['connection']=='Connected')
    monitor.command('toggle','mode-to-operate',expected_mode='Standby')
    wait(lambda:monitor.snapshot().get('status')=='Operate' and not monitor.controls.pending)
    monitor.command('toggle','mode-to-operate',expected_mode='Standby')
    self.assertEqual(monitor.mode_test_sent,1)
    monitor.controls.last_sent-=3
    monitor.command('toggle','mode-to-standby',expected_mode='Operate')
    wait(lambda:monitor.snapshot().get('status')=='Standby' and not monitor.controls.pending)
    self.assertEqual(monitor.simulator.sent.count(b'O'),2)
    with self.assertRaises(ValueError):monitor.command('toggle','extra-mode-command',expected_mode='Standby')
    self.assertEqual(len([h for h in monitor.command_history if h['phase']=='confirmed']),2)
   finally:monitor.disconnect();monitor.thread.join(3)
   with self.assertRaises(ValueError):monitor.connect()
 def test_rf_blocks_even_the_authorized_mode_command(self):
  monitor=Monitor(simulate=True,mode_test=True)
  monitor.state={'connection':'Connected','status':'Standby','_received':time.monotonic(),'transmitting':True}
  with self.assertRaisesRegex(ValueError,'Stop transmission'):monitor.command('toggle','no-rf-mode-123',expected_mode='Standby')
  self.assertEqual(monitor.mode_test_sent,0)
 def test_read_only_and_mode_test_are_mutually_exclusive(self):
  with self.assertRaises(ValueError):Monitor(read_only=True,mode_test=True)

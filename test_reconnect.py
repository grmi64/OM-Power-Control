"""Regressions for session closure and startup timing; amplifier socket mocked."""
import socket,unittest
from contextlib import contextmanager
from unittest.mock import patch
from live import Monitor
from test_live import FakeSocket

class ReconnectTests(unittest.TestCase):
 def test_remote_close_after_startup_is_not_accepted_as_telemetry(self):
  monitor=Monitor(allow_hardware=True,read_only=True)
  class ClosingSocket(FakeSocket):
   def recv(self,size):
    if self.sent.count(b'C')>=2:return b'COFF;'
    self.reads+=1
    if self.reads==1:return b'CON;'
    if self.reads==2:return b'STBY;PTTOFF;'
    if self.reads==3:return b'COFF;'
    monitor.stop.set();return b'TE64;'
  wire=ClosingSocket(monitor)
  with patch('session_protocol.socket.create_connection',return_value=wire):monitor.run()
  self.assertEqual(monitor.snapshot()['connection'],'Disconnected')
  self.assertIn('remote session closed',monitor.snapshot().get('error','').lower())
  self.assertTrue(set(wire.sent)<={b'C',b'?',b'#',b'F'})
 def test_slow_setup_does_not_spend_the_data_timeout(self):
  monitor=Monitor(allow_hardware=True,read_only=True);clock=[0.0]
  class SlowSocket:
   reads=0
   def sendall(self,data):pass
   def recv(self,size):
    self.reads+=1;clock[0]+=.2
    if self.reads==1:raise socket.timeout()
    monitor.stop.set();return b'STBY;PTTOFF;'
  wire=SlowSocket()
  @contextmanager
  def slow_session(*args,**kwargs):
   clock[0]=30.0;yield wire,b'CON;'
  with patch('live.amplifier_session',slow_session),patch('live.time.monotonic',side_effect=lambda:clock[0]):monitor.run()
  self.assertEqual(wire.reads,2)
  self.assertNotIn('No amplifier data',monitor.snapshot().get('error',''))
 def test_session_only_replies_cannot_keep_a_fake_live_connection(self):
  monitor=Monitor(allow_hardware=True,read_only=True);clock=[0.0]
  class SessionOnlySocket:
   def sendall(self,data):pass
   def recv(self,size):clock[0]+=2;return b'CON;'
  @contextmanager
  def session_only(*args,**kwargs):yield SessionOnlySocket(),b'CON;'
  with patch('live.amplifier_session',session_only),patch('live.time.monotonic',side_effect=lambda:clock[0]):monitor.run()
  self.assertEqual(monitor.snapshot()['connection'],'Disconnected')
  self.assertIn('No amplifier data',monitor.snapshot()['error'])

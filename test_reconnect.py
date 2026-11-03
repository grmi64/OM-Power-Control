"""Regressions for session closure and startup timing; amplifier socket mocked."""
import errno,socket,unittest
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
  self.assertTrue(set(wire.sent)<={b'C',b'?',b'#',b'F',b'1'})
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

class SettleTests(unittest.TestCase):
 def test_settings_and_reconnect_wait_for_a_closing_session(self):
  import threading,time
  with patch('live.settings.save',side_effect=lambda value:value):self.settle_waits()
 def settle_waits(self):
  import threading,time
  monitor=Monitor(simulate=True);monitor.stop.set();release=threading.Event()
  monitor.thread=threading.Thread(target=release.wait);monitor.thread.start()
  threading.Timer(.3,release.set).start();started=time.monotonic()
  monitor.configure({'model':'OM-4001A'})
  self.assertGreaterEqual(time.monotonic()-started,.25);self.assertFalse(monitor.thread.is_alive());self.assertEqual(monitor.settings['model'],'OM-4001A')
 def test_a_running_session_still_blocks_a_model_change(self):
  import threading
  with patch('live.settings.save',side_effect=lambda value:value):
   monitor=Monitor(simulate=True);monitor.settings['model']='OM-3501A';release=threading.Event();monitor.thread=threading.Thread(target=release.wait);monitor.thread.start()
   try:
    with self.assertRaisesRegex(ValueError,'Disconnect before changing'):monitor.configure({'model':'OM-4001A'})
   finally:release.set();monitor.thread.join()

class ConnectRetryTests(unittest.TestCase):
 """First-launch macOS Local Network prompts make the first TCP connects fail; retry those, only those."""
 def run_with(self,errors,retry_seconds=60):
  monitor=Monitor(allow_hardware=True,read_only=True);calls=[];states=[];wire=FakeSocket(monitor)
  def connect(*args,**kwargs):
   calls.append(1);states.append(monitor.snapshot())
   if len(calls)<=len(errors):raise errors[len(calls)-1]
   return wire
  with patch('session_protocol.socket.create_connection',side_effect=connect),patch('live.CONNECT_RETRY_DELAY',0.01),patch('live.CONNECT_RETRY_SECONDS',retry_seconds):monitor.run()
  return monitor,calls,states,wire
 def test_unreachable_then_allowed_connects_without_a_restart(self):
  errors=[OSError(errno.EHOSTUNREACH,'No route to host'),OSError(errno.EHOSTUNREACH,'No route to host'),socket.timeout('timed out')]
  monitor,calls,states,wire=self.run_with(errors)
  self.assertEqual(len(calls),4);self.assertIn(b'C',wire.sent)
  self.assertEqual(states[1]['connection'],'Connecting');self.assertIn('Local Network',states[1]['connect_note'])
  self.assertNotIn('error',states[1]);self.assertNotEqual(monitor.snapshot().get('error'),'No route to host')
 def test_refused_and_timed_out_are_also_retried(self):
  self.assertEqual(len(self.run_with([ConnectionRefusedError(errno.ECONNREFUSED,'refused'),TimeoutError()])[1]),3)
 def test_other_errors_are_not_retried(self):
  for error in (OSError(errno.EACCES,'Permission denied'),ConnectionError('Amplifier did not enter the remote session'),ValueError('bad')):
   monitor,calls,_,_=self.run_with([error]);self.assertEqual(len(calls),1,error);self.assertEqual(monitor.snapshot()['connection'],'Disconnected');self.assertEqual(monitor.snapshot()['error'],str(error))
 def test_gives_up_after_the_retry_window(self):
  monitor,calls,_,_=self.run_with([OSError(errno.EHOSTUNREACH,'No route to host')]*5,retry_seconds=0)
  self.assertEqual(len(calls),1);self.assertEqual(monitor.snapshot()['connection'],'Disconnected');self.assertIn('No route to host',monitor.snapshot()['error'])
 def test_disconnect_during_the_wait_stops_retrying(self):
  monitor=Monitor(allow_hardware=True,read_only=True);calls=[]
  def connect(*args,**kwargs):
   calls.append(1);monitor.stop.set();raise OSError(errno.EHOSTUNREACH,'No route to host')
  with patch('session_protocol.socket.create_connection',side_effect=connect),patch('live.CONNECT_RETRY_DELAY',0.01):monitor.run()
  self.assertEqual(len(calls),1);self.assertEqual(monitor.snapshot()['connection'],'Disconnected')
 def test_a_session_that_ended_after_connecting_is_not_retried(self):
  monitor=Monitor(allow_hardware=True,read_only=True);calls=[]
  class DropSocket(FakeSocket):
   def recv(self,n):raise OSError(errno.ETIMEDOUT,'timed out after connecting')
  def connect(*args,**kwargs):calls.append(1);return DropSocket(monitor)
  with patch('session_protocol.socket.create_connection',side_effect=connect),patch('live.CONNECT_RETRY_DELAY',0.01):monitor.run()
  self.assertEqual(len(calls),1);self.assertEqual(monitor.snapshot()['connection'],'Disconnected')

if __name__=='__main__':unittest.main()

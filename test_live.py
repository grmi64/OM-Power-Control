import unittest,socket,time
from unittest.mock import patch
from live import Monitor
class FakeSocket:
 def __init__(self,monitor):self.monitor=monitor;self.sent=[];self.reads=0
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def settimeout(self,n):pass
 def sendall(self,data):self.sent.append(data)
 def recv(self,n):
  if self.sent.count(b'C')>=2:return b'COFF;'
  self.reads+=1
  if self.reads==1:return b'CON;'
  if self.reads==2:return b'STBY;PTTOFF;'
  self.monitor.stop.set();return b'TE63;'
class Tests(unittest.TestCase):
 def test_only_poll_and_clean_disconnect(self):
  m=Monitor(allow_hardware=True);s=FakeSocket(m)
  with patch('live.socket.create_connection',return_value=s):m.run()
  self.assertEqual(s.sent,[b'C',b'?',b'#',b'F',b'C']);self.assertEqual(m.snapshot()['connection'],'Disconnected');self.assertIsNone(m.snapshot()['forward'])
 def test_worker_sends_toggle_once_and_confirms(self):
  m=Monitor(allow_hardware=True)
  class ControlSocket(FakeSocket):
   def recv(self,n):
    if self.sent.count(b'C')>=2:return b'COFF;'
    self.reads+=1
    if self.reads==1:return b'CON;'
    if self.reads==2:return b'STBY;PTTOFF;'
    if self.reads==3:
     m.command('toggle','test-command-1')
     return b'TE63;'
    if self.reads==4:return b'OPERATE;'
    m.stop.set();return b'TE63;'
  s=ControlSocket(m)
  with patch('live.socket.create_connection',return_value=s):m.run()
  self.assertEqual(s.sent.count(b'O'),1)
  self.assertEqual(m.controls.message,'Operating mode confirmed by amplifier')
 def test_stale_clears_readings(self):
  m=Monitor(allow_hardware=True);m.state={'connection':'Connected','_received':time.monotonic()-4,'_measurement':time.monotonic()-4,'forward':1433,'reflected':12,'swr':1.2}
  s=m.snapshot();self.assertEqual(s['connection'],'Stale');self.assertIsNone(s['forward'])
 def test_extra_telemetry_has_independent_freshness(self):
  m=Monitor(allow_hardware=True);m.state={'connection':'Connected','_received':99,'_field_times':{'plate_a':99,'grid_a_v':99,'grid_b_v':99,'frequency_khz':91},'plate_a':.86,'grid_a_v':75,'grid_b_v':150,'frequency_khz':14078,'screen_ma':-2}
  with patch('live.time.monotonic',return_value=100):
   v=m.snapshot();self.assertEqual(v['plate_a'],.86);self.assertEqual(v['grid_v'],-75);self.assertEqual(v['frequency_khz'],14078);self.assertIsNone(v['screen_ma'])
  m.state['_received']=104
  with patch('live.time.monotonic',return_value=104):
   v=m.snapshot();self.assertIsNone(v['plate_a']);self.assertIsNone(v['grid_v']);self.assertIsNone(v['frequency_khz'])
 def test_connection_failure(self):
  m=Monitor(allow_hardware=True)
  with patch('live.socket.create_connection',side_effect=OSError('Test unavailable')):m.run()
  self.assertEqual(m.snapshot()['connection'],'Disconnected');self.assertIn('Test unavailable',m.snapshot()['error'])
 def test_unchanged_binary_refreshes_revision(self):
  from decoder import Decoder
  d=Decoder();frame=b'='+bytes.fromhex('99050615fefe362b')+b';';d.feed(frame);d.feed(frame);self.assertEqual(d.measurement_revision,2)
 def test_confirmed_idle_survives_measurement_expiry_only_while_connected(self):
  from decoder import Decoder
  d=Decoder();d.feed(b'PTTON;='+bytes.fromhex('99050615fefe362b')+b';PTTOFF;')
  m=Monitor(allow_hardware=True);m.state={**d.state,'connection':'Connected','_received':99,'_measurement':10}
  with patch('live.time.monotonic',return_value=100):
   s=m.snapshot();self.assertEqual(s['forward'],0);self.assertEqual(s['reflected'],0);self.assertEqual(s['input'],0);self.assertIsNone(s['swr'])
  with patch('live.time.monotonic',return_value=104):
   s=m.snapshot();self.assertEqual(s['connection'],'Stale');self.assertIsNone(s['forward'])
  d.feed(b'PTTON;');m.state={**d.state,'connection':'Connected','_received':99,'_measurement':10}
  with patch('live.time.monotonic',return_value=100):self.assertIsNone(m.snapshot()['forward'])
 def test_startup_does_not_invent_idle_zero(self):
  from decoder import Decoder
  d=Decoder();d.feed(b'CON;TE63;');m=Monitor(allow_hardware=True);m.state={**d.state,'connection':'Connected','_received':99}
  with patch('live.time.monotonic',return_value=100):self.assertIsNone(m.snapshot()['forward'])
 def test_binary_measurement_clears_idle_latch(self):
  from decoder import Decoder
  d=Decoder();d.feed(b'PTTOFF;');self.assertTrue(d.state['rf_idle_confirmed'])
  d.feed(b'='+bytes.fromhex('99050615fefe362b')+b';');self.assertFalse(d.state['rf_idle_confirmed']);self.assertEqual(d.state['forward'],1433)
 def test_rf_without_transmit_start_message(self):
  from decoder import Decoder
  d=Decoder();d.feed(b'CON;='+bytes.fromhex('99050615fefe362b')+b';')
  self.assertTrue(d.state['transmitting']);self.assertEqual(d.state['status'],'Unknown')
  m=Monitor(allow_hardware=True);m.state={**d.state,'connection':'Connected','_received':time.monotonic(),'_measurement':time.monotonic()}
  with self.assertRaises(ValueError):m.command('toggle','request-123')
  d.feed(b'PTTOFF;');self.assertFalse(d.state['transmitting']);self.assertTrue(d.state['rf_idle_confirmed'])
 def test_zero_measurement_does_not_clear_transmit_start(self):
  from decoder import Decoder
  d=Decoder();d.feed(b'PTTON;='+bytes.fromhex('00000000fefe362b')+b';');self.assertTrue(d.state['transmitting'])
  d.feed(b'PTTOFF;');self.assertFalse(d.state['transmitting'])
 def test_input_rf_without_forward_power(self):
  from decoder import Decoder
  d=Decoder();d.feed(b'='+bytes.fromhex('00000001fefe362b')+b';');self.assertTrue(d.state['transmitting'])
 def test_idle_status_query_refreshes_mode_without_operating_commands(self):
  clock=[100.0];m=Monitor(allow_hardware=True)
  class PollSocket(FakeSocket):
   def recv(self,n):
    if self.sent.count(b'C')>=2:return b'COFF;'
    self.reads+=1
    if self.reads==1:return b'CON;'
    clock[0]+=2.1
    if self.reads==2:return b'ST1110- HEXBEAM;'
    if self.reads==3:return b'ST1100- HEXBEAM;'
    m.stop.set();return b'TE63;'
  sock=PollSocket(m)
  with patch('live.socket.create_connection',return_value=sock),patch('live.time.monotonic',side_effect=lambda:clock[0]):m.run()
  self.assertGreaterEqual(sock.sent.count(b'?'),2);self.assertTrue(set(sock.sent)<={b'C',b'?',b'#',b'F'})
if __name__=='__main__':unittest.main()

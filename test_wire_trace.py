"""Wire tracing preserves exact bytes and cannot bypass access policies."""
import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from live import Monitor
from session_protocol import amplifier_session
from test_session_protocol import Socket
from test_live import FakeSocket
from wire_trace import WireTrace,TracedSocket

class WireTraceTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'trace.jsonl'
 def tearDown(self):self.temp.cleanup()
 def rows(self):return [json.loads(line) for line in self.path.read_text().splitlines()]
 def test_exact_rx_padding_and_tx_bytes_no_injected_commands(self):
  trace=WireTrace(self.path);raw=Socket([b'\x00PTTOFF;',b'']);wire=TracedSocket(raw,trace)
  wire.sendall(b'#');self.assertEqual(wire.recv(100),b'\x00PTTOFF;');self.assertEqual(wire.recv(100),b'');trace.close()
  self.assertEqual(raw.sent,[b'#']);rows=self.rows()
  self.assertEqual([(r['kind'],r['hex']) for r in rows],[('tx','23'),('rx','005054544f46463b'),('rx','')])
 def test_trace_size_limit_stops_logging_without_affecting_writes(self):
  trace=WireTrace(self.path,max_bytes=250);raw=Socket([]);wire=TracedSocket(raw,trace)
  with self.assertLogs(level='WARNING'):
   for _ in range(20):wire.sendall(b'#')
  trace.close();self.assertEqual(raw.sent,[b'#']*20);self.assertLessEqual(self.path.stat().st_size,250);self.rows()
 def test_io_failure_does_not_change_socket_result_or_retry(self):
  trace=WireTrace(self.path);trace.file.close();trace.file=Mock();trace.file.write.side_effect=OSError('disk full')
  raw=Socket([b'PTTOFF;']);wire=TracedSocket(raw,trace)
  with self.assertLogs(level='ERROR'):self.assertEqual(wire.recv(100),b'PTTOFF;')
  wire.sendall(b'#');self.assertEqual(raw.sent,[b'#']);self.assertIsNone(trace.file)
 def test_read_only_policy_blocks_power_before_traced_socket(self):
  trace=WireTrace(self.path);raw=Socket([b'CON;',b'COFF;'])
  with patch('session_protocol.socket.create_connection',return_value=raw):
   with amplifier_session(('192.0.2.1',10001),threading.Event(),read_only=True,trace=trace) as (wire,_):
    for data in (b'Y',b'Z',b'O',b'L'):
     with self.assertRaises(ValueError):wire.sendall(data)
    wire.sendall(b'#')
  trace.close();self.assertEqual(raw.sent,[b'C',b'#',b'C'])
  self.assertEqual([r['hex'] for r in self.rows() if r['kind']=='tx'],['43','23','43'])
 def test_worker_records_raw_and_decoded_rf_off(self):
  trace=WireTrace(self.path);m=Monitor(allow_hardware=True,read_only=True,trace=trace);raw=FakeSocket(m)
  with patch('session_protocol.socket.create_connection',return_value=raw):m.run()
  trace.close();rows=self.rows()
  self.assertTrue(any(r['kind']=='rx' and b'PTTOFF;' in bytes.fromhex(r['hex']) for r in rows))
  self.assertTrue(any(r['kind']=='decoded' and 'PTTOFF' in r['tokens'] and r['rf_idle_confirmed'] for r in rows))
  self.assertTrue(set(raw.sent)<={b'C',b'?',b'#',b'F'})

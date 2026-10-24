"""Read-only hardware policy verified offline before connecting equipment."""
import json,threading,time,unittest,urllib.request,urllib.error
from unittest.mock import patch
from controls import COMMANDS
from live import Monitor,create_server
from session_protocol import ReadOnlySocket,amplifier_session
from test_session_protocol import Socket

class ReadOnlyTests(unittest.TestCase):
 def test_socket_allowlist_excludes_every_operating_and_tuning_command(self):
  wire=Socket([]);guard=ReadOnlySocket(wire)
  for data in ReadOnlySocket.ALLOWED:guard.sendall(data)
  before=list(wire.sent)
  for data in [*(v[0] for v in COMMANDS.values()),b'&',b'?#',b'',b'PTT',b'FREQ14000']:
   with self.assertRaisesRegex(ValueError,'Read-only'):guard.sendall(data)
  self.assertEqual(wire.sent,before)
 def test_read_only_session_guard_covers_handshake_poll_and_close(self):
  wire=Socket([b'CON;',b'COFF;']);stop=threading.Event()
  with patch('session_protocol.socket.create_connection',return_value=wire),patch.object(stop,'wait',return_value=False):
   with amplifier_session(('approved-address',10001),stop,read_only=True) as (sock,data):
    self.assertEqual(data,b'CON;');sock.sendall(b'?');sock.sendall(b'#');sock.sendall(b'F')
    with self.assertRaises(ValueError):sock.sendall(b'O')
  self.assertEqual(wire.sent,[b'C',b'?',b'#',b'F',b'C'])
 def test_monitor_rejects_standalone_and_shared_controls(self):
  monitor=Monitor(simulate=True,read_only=True)
  monitor.state={'connection':'Connected','status':'Operate','_received':time.monotonic(),'autotune_phase':'tuning','transmitting':True}
  for source in ('standalone','DXC'):
   for action in COMMANDS:
    with self.assertRaisesRegex(ValueError,'Read-only'):monitor.command(action,'readonly-'+action,source=source)
  self.assertIsNone(monitor.controls.pending);self.assertTrue(monitor.snapshot()['read_only'])
 def test_worker_never_dispatches_even_an_injected_pending_command(self):
  monitor=Monitor(simulate=True,read_only=True);monitor.connect()
  try:
   deadline=time.monotonic()+3
   while monitor.snapshot()['connection']!='Connected':
    self.assertLess(time.monotonic(),deadline);time.sleep(.02)
   with monitor.lock:monitor.controls.pending={'action':'toggle','id':'injected-command','sent':None}
   time.sleep(.15)
  finally:monitor.disconnect();monitor.thread.join(3)
  self.assertTrue(set(monitor.simulator.sent)<=ReadOnlySocket.ALLOWED)
  self.assertNotIn(b'O',monitor.simulator.sent)
 def test_http_cannot_enable_controls_in_read_only_process(self):
  monitor=Monitor(simulate=True,read_only=True);server=create_server(monitor)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  base=f'http://127.0.0.1:{server.server_port}'
  try:
   for action in COMMANDS:
    req=urllib.request.Request(base+'/control/'+action,json.dumps({'id':'readonly-test-'+action}).encode(),headers={'X-OM-Token':server.token,'Content-Type':'application/json'})
    with self.assertRaises(urllib.error.HTTPError) as exc:urllib.request.urlopen(req,timeout=3)
    self.assertEqual(exc.exception.code,409);self.assertIn(b'Read-only',exc.exception.read())
   self.assertIsNone(monitor.controls.pending)
  finally:server.shutdown();server.server_close();thread.join(2)

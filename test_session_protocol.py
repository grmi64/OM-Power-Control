import unittest,threading,socket
from unittest.mock import patch
from session_protocol import establish,release,amplifier_session,SessionCancelled
class Socket:
 def __init__(self,replies):self.replies=list(replies);self.sent=[]
 def sendall(self,data):self.sent.append(data)
 def recv(self,n):return self.replies.pop(0) if self.replies else b''
 def settimeout(self,n):pass
 def __enter__(self):return self
 def __exit__(self,*args):pass
class Tests(unittest.TestCase):
 def test_fresh_session(self):
  s=Socket([b'C',b'ON;']);self.assertEqual(establish(s,threading.Event()),b'CON;');self.assertEqual(s.sent,[b'C'])
 def test_stale_remote_session_normalizes_on_same_socket(self):
  s=Socket([b'COFF;',b'CON;']);self.assertEqual(establish(s,threading.Event()),b'COFF;CON;');self.assertEqual(s.sent,[b'C',b'C'])
 def test_repeated_off_is_bounded(self):
  s=Socket([b'COFF;',b'COFF;'])
  with self.assertRaises(ConnectionError):establish(s,threading.Event())
  self.assertEqual(s.sent,[b'C',b'C'])
 def test_no_blind_retry_without_ack(self):
  s=Socket([b''])
  with self.assertRaises(ConnectionError):establish(s,threading.Event())
  self.assertEqual(s.sent,[b'C'])
 def test_clean_close(self):
  s=Socket([b'PTTOFF;CO',b'FF;']);release(s);self.assertEqual(s.sent,[b'C'])
 def test_close_normalizes_only_on_explicit_on(self):
  s=Socket([b'CON;',b'COFF;']);release(s);self.assertEqual(s.sent,[b'C',b'C'])
 def test_cancel_before_handshake(self):
  s=Socket([]);stop=threading.Event();stop.set()
  with patch('session_protocol.socket.create_connection',return_value=s):
   with self.assertRaises(SessionCancelled):
    with amplifier_session(('test',10001),stop):pass
  self.assertEqual(s.sent,[])
 def test_context_cleans_up_on_exception(self):
  s=Socket([b'CON;',b'COFF;']);stop=threading.Event()
  with patch('session_protocol.socket.create_connection',return_value=s),patch.object(stop,'wait',return_value=False):
   with self.assertRaises(ValueError):
    with amplifier_session(('test',10001),stop):raise ValueError('test')
  self.assertEqual(s.sent,[b'C',b'C'])
if __name__=='__main__':unittest.main()

"""Offline session cleanup preserves the primary failure and records close errors."""
import threading,unittest
from unittest.mock import patch
from simulator import SimulatedAmplifier,simulated_session

class SimulatedSessionTests(unittest.TestCase):
 def test_cleanup_failure_keeps_primary_error(self):
  for failure in (TimeoutError('No amplifier data for 10 seconds'),ConnectionError('Amplifier closed the connection')):
   events=[]
   with self.subTest(failure=failure),patch('session_protocol.release',side_effect=ConnectionError('No connection acknowledgement')):
    with self.assertRaises(type(failure)) as caught:
     with simulated_session(SimulatedAmplifier(),threading.Event(),events.append):raise failure
    self.assertIs(caught.exception,failure)
    self.assertIn('Remote session close: No connection acknowledgement',events)
 def test_clean_exit_records_unconfirmed_release(self):
  events=[]
  with patch('session_protocol.release',side_effect=ConnectionError('Unconfirmed close')):
   with simulated_session(SimulatedAmplifier(),threading.Event(),events.append):pass
  self.assertIn('Remote session close: Unconfirmed close',events)

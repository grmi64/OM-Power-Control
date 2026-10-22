import unittest,time
from unittest.mock import patch
from controls import Controls
class Tests(unittest.TestCase):
 def state(self,**kw):return {'connection':'Connected','_received':time.monotonic(),'status':'Standby','transmitting':False,**kw}
 def test_toggle_once_and_confirm(self):
  c=Controls();s=self.state();c.request('toggle','request-123',s);self.assertEqual(c.take(s),b'O');self.assertIsNone(c.take(s));c.observe(['TE63']);self.assertIsNotNone(c.pending);c.observe(['OPERATE']);self.assertIsNone(c.pending);c.request('toggle','request-123',s);self.assertIsNone(c.take(s))
 def test_no_retry_after_timeout(self):
  c=Controls();s=self.state();c.request('off','request-123',s);self.assertEqual(c.take(s),b'Z');c.pending['sent']-=6;c.tick();self.assertTrue(c.uncertain);self.assertIsNone(c.take(s))
  with self.assertRaises(ValueError):c.request('off','request-456',s)
 def test_power_confirmations(self):
  for action,token,wire,status in [('on','WA180',b'Y','Off'),('off','COON',b'Z','Standby')]:
   c=Controls();s=self.state(status=status);c.request(action,'request-123',s);self.assertEqual(c.take(s),wire);c.observe([token]);self.assertIsNone(c.pending);self.assertFalse(c.uncertain)
 def test_guards(self):
  for change in [{'transmitting':True},{'status':'Warming up'},{'status':'Cooling down'},{'connection':'Disconnected'},{'_received':time.monotonic()-5}]:
   c=Controls()
   with self.assertRaises(ValueError):c.request('toggle','request-123',self.state(**change))
 def test_transmit_after_queue(self):
  c=Controls();c.request('toggle','request-123',self.state());self.assertIsNone(c.take(self.state(transmitting=True)));self.assertIsNone(c.pending)
 def test_loss_never_requeues(self):
  c=Controls();s=self.state();c.request('toggle','request-123',s);c.take(s);c.lost();self.assertTrue(c.uncertain);self.assertIsNone(c.take(s))
 def test_expected_mode_request_and_dispatch(self):
  c=Controls()
  with self.assertRaises(ValueError):c.request('toggle','request-123',self.state(status='Operate'),'Standby')
  c.request('toggle','request-456',self.state(status='Standby'),'Standby')
  self.assertIsNone(c.take(self.state(status='Operate')));self.assertIsNone(c.pending)
 def test_expected_confirmation_and_mismatch(self):
  for start,reply,uncertain in [('Standby','OPERATE',False),('Operate','STBY',False),('Standby','STBY',True)]:
   c=Controls();s=self.state(status=start);c.request('toggle','request-123',s,start);self.assertEqual(c.take(s),b'O');c.observe([reply]);self.assertEqual(c.uncertain,uncertain);self.assertIsNone(c.pending)
 def test_stale_or_countdown_before_dispatch(self):
  for state in [self.state(_received=time.monotonic()-4),self.state(status='Cooling down')]:
   c=Controls();c.request('off','request-123',self.state());self.assertIsNone(c.take(state));self.assertIsNone(c.pending)
 def test_power_state_change_before_dispatch(self):
  for action,start,end in [('on','Off','Standby'),('off','Standby','Off'),('toggle','Standby','Off')]:
   c=Controls();c.request(action,'request-123',self.state(status=start));self.assertIsNone(c.take(self.state(status=end)));self.assertIsNone(c.pending)
 def test_redundant_power_actions(self):
  for action,status in [('on','Operate'),('on','Standby'),('on','On'),('off','Off')]:
   with self.assertRaises(ValueError):Controls().request(action,'request-123',self.state(status=status))
if __name__=='__main__':unittest.main()

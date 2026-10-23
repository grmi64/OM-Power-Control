import unittest,time
from controls import Controls
class AutoTuneControlTests(unittest.TestCase):
 def s(self,**kw):return dict(connection='Connected',_received=time.monotonic(),status='Operate',transmitting=False,**kw)
 def test_verified_two_phase_sequence(self):
  c=Controls();s=self.s();c.request('autotune','start-1234',s);self.assertEqual(c.take(s),b'L');self.assertIsNone(c.take(s));c.observe(['AUTO']);s['autotune_phase']='entered';self.assertEqual(c.take(s),b'&');self.assertIsNone(c.take(s));c.observe(['AUTO:WAITING FOR INPUT POWER']);self.assertIsNone(c.pending);self.assertFalse(c.uncertain)
 def test_no_arm_without_ack_or_after_rf_starts(self):
  c=Controls();s=self.s();c.request('autotune','start-1234',s);c.take(s);c.observe(['IP0']);self.assertIsNone(c.take(s));c.observe(['AUTO']);s.update(autotune_phase='entered',transmitting=True);self.assertIsNone(c.take(s));self.assertIsNone(c.pending)
 def test_timeout_never_retries(self):
  c=Controls();s=self.s();c.request('autotune','start-1234',s);c.take(s);c.pending['sent']-=6;c.tick();self.assertTrue(c.uncertain);self.assertIsNone(c.take(s))
 def test_unknown_response_blocks_arm(self):
  c=Controls();s=self.s();c.request('autotune','start-1234',s);c.take(s);c.observe(['AUTO:UNEXPECTED']);self.assertTrue(c.uncertain);self.assertIsNone(c.take(s))
 def test_waiting_exit_only(self):
  c=Controls();s=self.s(autotune_phase='waiting');c.request('autotune-exit','exit-1234',s);self.assertEqual(c.take(s),b'*');c.observe(['AUTOESC']);self.assertIsNone(c.pending)
  for phase in ['tuning','unknown','entered','succeeded',None]:
   with self.assertRaises(ValueError):Controls().request('autotune-exit','exit-1234',self.s(autotune_phase=phase))
 def test_existing_controls_and_duplicate_start_guarded(self):
  for phase in ['entered','waiting','tuning','unknown']:
   for action in ['toggle','on','off','autotune']:
    with self.assertRaises(ValueError):Controls().request(action,'request-123',self.s(autotune_phase=phase))
  with self.assertRaises(ValueError):Controls().request('autotune','start-1234',{**self.s(),'status':'Standby'})
 def test_loss_between_stages_stays_uncertain(self):
  c=Controls();s=self.s();c.request('autotune','start-1234',s);c.take(s);c.observe(['AUTO']);c.lost();self.assertTrue(c.uncertain);self.assertIsNone(c.take(s))
 def test_stop_is_allowed_with_rf_and_no_cooldown_retry(self):
  c=Controls();s=self.s(autotune_phase='tuning');s['transmitting']=True;c.last_sent=time.monotonic();c.request('autotune-stop','stop-1234',s);self.assertEqual(c.take(s),b'8');self.assertIsNone(c.take(s));c.observe(['STOP']);self.assertIsNone(c.pending);self.assertFalse(c.uncertain)
  for phase in ['entered','waiting','aborted','succeeded',None]:
   with self.assertRaises(ValueError):Controls().request('autotune-stop','stop-1234',self.s(autotune_phase=phase))
 def test_coalesced_entry_ack_and_waiting_before_arm(self):
  c=Controls();s=self.s();c.request('autotune','start-1234',s);self.assertEqual(c.take(s),b'L');c.observe(['AUTO','AUTO:WAITING FOR INPUT POWER']);s['autotune_phase']='waiting';self.assertEqual(c.take(s),b'&');c.observe(['AUTO:WAITING FOR INPUT POWER']);self.assertIsNone(c.pending)
 def test_rf_aborted_exit_requires_default_ack(self):
  c=Controls();s=self.s(autotune_phase='aborted',autotune_abort_origin='rf_lost');c.request('autotune-exit','exit-1234',s);self.assertEqual(c.take(s),b'*');c.observe(['AUTOESC']);self.assertIsNotNone(c.pending);c.observe(['SAVE DEFAULT']);self.assertIsNone(c.pending);self.assertIn('default settings',c.message)
  for origin in ['unknown',None]:
   with self.assertRaises(ValueError):Controls().request('autotune-exit','exit-1234',self.s(autotune_phase='aborted',autotune_abort_origin=origin))
 def test_rf_abort_exit_blocked_if_rf_resumes(self):
  c=Controls();s=self.s(autotune_phase='aborted',autotune_abort_origin='rf_lost');c.request('autotune-exit','exit-1234',s);s['transmitting']=True;self.assertIsNone(c.take(s));self.assertIsNone(c.pending)

 def test_stop_abort_exit_saves_current_settings_without_success(self):
  c=Controls();s=self.s(autotune_phase='aborted',autotune_abort_origin='stop');c.request('autotune-exit','exit-1234',s);self.assertEqual(c.take(s),b'*');c.observe(['AUTO:AUTOTUNE ABORTED']);self.assertIsNotNone(c.pending);c.observe(['SAVE USER']);self.assertIsNone(c.pending);self.assertIn('not successful',c.message)
 def test_stuck_stop_exit_times_out_without_retry(self):
  c=Controls();s=self.s(autotune_phase='aborted',autotune_abort_origin='stop');c.request('autotune-exit','exit-1234',s);c.take(s);c.observe(['AUTO:AUTOTUNE ABORTED']);c.pending['sent']-=6;c.tick();self.assertTrue(c.uncertain);self.assertIsNone(c.take(s))

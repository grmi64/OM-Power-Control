"""Manufacturer-compatible saved-tune RF-off recovery; no amplifier access."""
import unittest
from decoder import Decoder

class PostTuneRFOffTests(unittest.TestCase):
 def tuning(self):
  d=Decoder();d.feed(b'OPERATE;AUTO;PTTON;AUTO:AUTOTUNE IN PROGRESS;IP1450;')
  return d
 def saved(self):
  d=self.tuning();d.feed(b'AUTO:AUTOTUNE DONE;SAVE USER;');return d
 def test_saved_tune_fresh_positive_to_zero_current_confirms_idle(self):
  d=self.saved();d.feed(b'IP1401;');self.assertTrue(d.state['transmitting'])
  d.feed(b'IP0;')
  self.assertFalse(d.state['transmitting']);self.assertTrue(d.state['rf_idle_confirmed'])
  self.assertEqual(d.state['rf_idle_source'],'post-tune-current-transition')
  self.assertTrue(d.state['autotune_saved']);self.assertEqual(d.state['autotune_phase'],'succeeded')
  self.assertNotIn('PTTOFF',d.tokens,'Compatibility detection must not invent a wire token')
  self.assertEqual([d.state[k] for k in ('forward','reflected','input')],[0,0,0])
 def test_zero_outside_saved_tune_does_not_clear_guard(self):
  for stream in (b'OPERATE;PTTON;IP1450;IP0;',b'OPERATE;AUTO;PTTON;IP1450;AUTO:AUTOTUNE DONE;IP0;',b'OPERATE;AUTO;PTTON;AUTO:AUTOTUNE DONE;SAVE USER;IP0;',b'OPERATE;AUTO;PTTON;IP1450;AUTO:AUTOTUNE DONE;IP0;SAVE USER;IP0;'):
   with self.subTest(stream=stream):
    d=Decoder();d.feed(stream);self.assertTrue(d.state['transmitting']);self.assertFalse(d.state.get('rf_idle_confirmed',False))
 def test_aborted_or_stopped_saved_tune_does_not_arm_recovery(self):
  for end in (b'AUTO:AUTOTUNE ABORTED;SAVE USER;',b'STOP;AUTO:AUTOTUNE ABORTED;SAVE USER;',b'AUTOESC;SAVE USER;',b'AUTO:UNEXPECTED;SAVE USER;'):
   with self.subTest(end=end):
    d=self.tuning();d.feed(end+b'IP0;');self.assertTrue(d.state['transmitting'])
 def test_nonzero_current_and_non_rf_updates_do_not_confirm_idle(self):
  for value in (b'IP1;',b'IP-0;',b'IP0.0;'):
   with self.subTest(value=value):
    d=self.saved();d.feed(value+b'TE64;UP3400;\x00\x00;')
    self.assertTrue(d.state['transmitting']);self.assertFalse(d.state['rf_idle_confirmed'])
 def test_new_transmit_start_and_duplicate_save_cannot_rearm_old_tune(self):
  for restart in (b'PTTON;',b'STBY;OPERATE;'):
   with self.subTest(restart=restart):
    d=self.saved();d.feed(restart+b'IP1450;SAVE USER;IP0;')
    self.assertTrue(d.state['transmitting']);self.assertFalse(d.state['rf_idle_confirmed'])
 def test_new_rf_after_recovery_reactivates_guard(self):
  d=self.saved();d.feed(b'IP0;');self.assertFalse(d.state['transmitting'])
  d.feed(b'='+bytes.fromhex('99050615fefe362b')+b';')
  self.assertTrue(d.state['transmitting']);self.assertFalse(d.state['rf_idle_confirmed'])
  d.feed(b'IP1450;SAVE USER;IP0;');self.assertTrue(d.state['transmitting'])
 def test_recovery_works_with_fragmented_null_padded_current(self):
  d=self.saved()
  for byte in b'\x00IP1401;\x00IP0;':d.feed(bytes([byte]))
  self.assertFalse(d.state['transmitting']);self.assertTrue(d.state['rf_idle_confirmed'])
 def test_explicit_ptt_off_works_without_tune_and_cancels_recovery(self):
  d=Decoder();d.feed(b'PTTON;PTTOFF;')
  self.assertFalse(d.state['transmitting']);self.assertEqual(d.state['rf_idle_source'],'ptt-off-message')
  d=self.saved();d.feed(b'PTTOFF;PTTON;IP1450;IP0;');self.assertTrue(d.state['transmitting'])

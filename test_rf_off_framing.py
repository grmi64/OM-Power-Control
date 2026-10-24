"""Offline framing regressions using synthetic RF events and observed NUL padding."""
import time,unittest
from decoder import Decoder
from live import Monitor

class RFOffFramingTests(unittest.TestCase):
 def test_null_prefixed_stop_after_saved_tune_at_every_split(self):
  stream=b'PTTON;='+bytes.fromhex('aa097a15010a7341')+b';AUTO:AUTOTUNE DONE;SAVE USER;\x00\x00PTTOFF;TE64;'
  for split in range(len(stream)+1):
   with self.subTest(split=split):
    d=Decoder();d.feed(stream[:split]);d.feed(stream[split:])
    self.assertFalse(d.state['transmitting']);self.assertTrue(d.state['rf_idle_confirmed']);self.assertEqual(d.state['forward'],0)
    self.assertEqual(d.state['autotune_phase'],'succeeded');self.assertTrue(d.state['autotune_saved'])
 def test_one_byte_chunks_and_padding_between_binary_and_ascii(self):
  d=Decoder()
  for byte in b'\x00PTTON;\x00='+bytes.fromhex('00000001fefe003b')+b';\x00PTTOFF;':d.feed(bytes([byte]))
  self.assertFalse(d.state['transmitting']);self.assertTrue(d.state['rf_idle_confirmed']);self.assertEqual(d.buffer,b'')
 def test_nulls_do_not_damage_binary_payload_or_confirm_idle(self):
  d=Decoder();d.feed(b'PTTON;\x00='+bytes.fromhex('00000001fefe003b')+b';')
  self.assertTrue(d.state['transmitting']);self.assertEqual(d.state['input'],1);self.assertFalse(d.state['rf_idle_confirmed'])
  revision=d.field_revisions['rf'];d.feed(b'\x00\x00TE64;\x00')
  self.assertTrue(d.state['transmitting']);self.assertFalse(d.state['rf_idle_confirmed']);self.assertEqual(d.field_revisions['rf'],revision)
 def test_padding_before_plate_current_is_not_part_of_token(self):
  d=Decoder();d.feed(b'\x00');d.feed(b'\x00IP0;UP3400;')
  self.assertEqual(d.state['plate_a'],0);self.assertEqual(d.tokens,['IP0','UP3400'])
 def test_embedded_null_is_not_silently_reinterpreted_as_rf_off(self):
  d=Decoder();d.feed(b'PTTON;PTT\x00OFF;TE64;')
  self.assertTrue(d.state['transmitting']);self.assertFalse(d.state['rf_idle_confirmed'])
 def test_verified_stop_releases_guard_without_timing_or_temperature_inference(self):
  d=Decoder();d.feed(b'OPERATE;PTTON;AUTO:AUTOTUNE DONE;SAVE USER;\x00PTTOFF;')
  m=Monitor(allow_hardware=True);m.state={**d.state,'connection':'Connected','_received':time.monotonic()}
  m.command('toggle','offline-standby-123',expected_mode='Operate')
  self.assertEqual(m.controls.pending['action'],'toggle')
  self.assertIsNone(m.thread,'Offline guard check must not open any amplifier socket')

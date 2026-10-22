import unittest,os
from pathlib import Path
from decoder import Decoder,replay
CAPTURE_DIR=Path(os.environ['OM_CAPTURE_DIRECTORY']) if os.environ.get('OM_CAPTURE_DIRECTORY') else None
class Tests(unittest.TestCase):
 def test_fragmentation(self):
  msg=b'PTTON;='+bytes.fromhex('99050615fefe362b')+b';PTTOFF;'
  baseline=Decoder().feed(msg)
  for cut in range(len(msg)+1):
   d=Decoder();self.assertEqual(d.feed(msg[:cut])+d.feed(msg[cut:]),baseline)
  reading=baseline[1];self.assertEqual(reading['forward'],1433);self.assertEqual(reading['reflected'],12);self.assertEqual(reading['input'],21);self.assertEqual(round(reading['swr'],1),1.2)
 def test_binary_delimiters(self):
  d=Decoder();r=d.feed(b'='+bytes([59,5,6,21,0,61,59,0])+b';');self.assertEqual(r[0]['forward'],1339)
 @unittest.skipUnless(CAPTURE_DIR,'Optional private hardware capture not supplied')
 def test_power_sequence(self):
  rows=replay(CAPTURE_DIR/'OM3501A-controls.pcapng');states={x['status'] for x in rows};self.assertTrue({'Operate','Standby','Cooling down','Off','Warming up','On'}<=states)
 @unittest.skipUnless(CAPTURE_DIR,'Optional private hardware capture not supplied')
 def test_readings(self):
  rows=replay(CAPTURE_DIR/'OM3501A-readings.pcapng');r=[x for x in rows if x.get('forward')==1433 and x.get('input')==21];self.assertTrue(r);self.assertEqual(rows[-1]['forward'],0);self.assertFalse(rows[-1]['transmitting']);self.assertAlmostEqual(rows[-1]['time'],49.012,places=2)
 def test_verified_startup_codes_and_fragmentation(self):
  for code,mode in [('1110','Operate'),('1100','Standby')]:
   msg=('ST'+code+'- HEXBEAM;').encode()
   for cut in range(len(msg)+1):
    d=Decoder();d.feed(msg[:cut]);d.feed(msg[cut:]);self.assertEqual(d.state['status'],mode)
 def test_transmit_cycle_preserves_status_query_mode(self):
  d=Decoder();d.feed(b'ST1110- HEXBEAM;='+bytes.fromhex('99050615fefe362b')+b';');self.assertTrue(d.state['transmitting']);self.assertEqual(d.state['status'],'Operate')
  d.feed(b'PTTOFF;TE66;');self.assertFalse(d.state['transmitting']);self.assertEqual(d.state['status'],'Operate');self.assertEqual(d.state['forward'],0)
 def test_query_recovers_missed_front_panel_mode_change(self):
  d=Decoder();d.feed(b'ST1110- HEXBEAM;');d.feed(b'ST1100- HEXBEAM;');self.assertEqual(d.state['status'],'Standby')
 def test_unverified_code_does_not_claim_known_mode(self):
  d=Decoder();d.feed(b'ST1110- HEXBEAM;ST1120- HEXBEAM;');self.assertEqual(d.state['status'],'Unknown')
if __name__=='__main__':unittest.main()

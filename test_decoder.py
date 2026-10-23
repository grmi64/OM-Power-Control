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
 def test_extended_fields_and_fragmentation(self):
  msg=b'IP862;UP3096;UGA75;UGB150;US337;UHA27.8;UHB27.8;UM239;TE64;FR14078;='+bytes.fromhex('99050615fefe362b')+b';'
  for cut in range(len(msg)+1):
   d=Decoder();d.feed(msg[:cut]);d.feed(msg[cut:]);s=d.state
   for key,value in {'plate_a':.862,'plate_v':3096,'grid_a_v':75,'grid_b_v':150,'screen_v':337,'heater_a_v':27.8,'mains_v':239,'temperature_c':32,'frequency_khz':14078,'screen_ma':-2}.items():self.assertEqual(s[key],value)
   self.assertAlmostEqual(s['gain_db'],18.34,places=2)
  d.feed(b'PTTOFF;');self.assertIsNone(d.state['gain_db'])
 def test_binary_delimiters(self):
  d=Decoder();r=d.feed(b'='+bytes([59,5,6,21,0,61,59,0])+b';');self.assertEqual(r[0]['forward'],1339)
 @unittest.skipUnless(CAPTURE_DIR,'Optional private hardware capture not supplied')
 def test_power_sequence(self):
  rows=replay(CAPTURE_DIR/'OM3501A-controls.pcapng');states={x['status'] for x in rows};self.assertTrue({'Operate','Standby','Cooling down','Off','Warming up','On'}<=states)
 @unittest.skipUnless(CAPTURE_DIR,'Optional private hardware capture not supplied')
 def test_readings(self):
  rows=replay(CAPTURE_DIR/'OM3501A-readings.pcapng');r=[x for x in rows if x.get('forward')==1433 and x.get('input')==21];self.assertTrue(r);self.assertEqual(rows[-1]['forward'],0);self.assertFalse(rows[-1]['transmitting']);self.assertAlmostEqual(rows[-1]['time'],49.012,places=2)
 def test_verified_startup_codes_and_fragmentation(self):
  for code,mode in [('1110','Operate'),('1100','Standby'),('2000','Off')]:
   msg=('ST'+code+'- HEXBEAM;').encode()
   for cut in range(len(msg)+1):
    d=Decoder();d.feed(msg[:cut]);d.feed(msg[cut:]);self.assertEqual(d.state['status'],mode)
 def test_transmit_cycle_preserves_status_query_mode(self):
  d=Decoder();d.feed(b'ST1110- HEXBEAM;='+bytes.fromhex('99050615fefe362b')+b';');self.assertTrue(d.state['transmitting']);self.assertEqual(d.state['status'],'Operate')
  d.feed(b'PTTOFF;TE66;');self.assertFalse(d.state['transmitting']);self.assertEqual(d.state['status'],'Operate');self.assertEqual(d.state['forward'],0)
 def test_query_recovers_missed_front_panel_mode_change(self):
  d=Decoder();d.feed(b'ST1110- HEXBEAM;');d.feed(b'ST1100- HEXBEAM;');self.assertEqual(d.state['status'],'Standby')
 def test_antenna_selection_is_separate_from_operating_mode(self):
  for code,name,mode,antenna in [('1110','HEXBEAM','Operate',1),('2110','DOUBLET','Operate',2),('1100','HEXBEAM','Standby',1),('2100','DOUBLET','Standby',2)]:
   msg=('ST'+code+'- '+name+';').encode()
   for cut in range(len(msg)+1):
    d=Decoder();d.feed(msg[:cut]);d.feed(msg[cut:]);self.assertEqual(d.state['status'],mode);self.assertEqual(d.state['antenna_name'],name);self.assertEqual(d.state['antenna_number'],antenna)
  d=Decoder();d.feed(b'ST2110- DOUBLET;PTTON;PTTOFF;ST2110- DOUBLET;');self.assertEqual(d.state['status'],'Operate')
  d.feed(b'ST2000- DOUBLET;');self.assertEqual(d.state['status'],'Off');self.assertIsNone(d.state['antenna_number'])
 def test_unverified_code_does_not_claim_known_mode(self):
  d=Decoder();d.feed(b'ST1110- HEXBEAM;ST1120- HEXBEAM;');self.assertEqual(d.state['status'],'Unknown')
if __name__=='__main__':unittest.main()

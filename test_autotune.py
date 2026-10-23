import unittest,os
from pathlib import Path
from decoder import Decoder,replay
class AutoTuneTests(unittest.TestCase):
 def test_fragmented_states_and_saved_confirmation(self):
  d=Decoder()
  for b in b'AUTO;AUTO:WAITING FOR INPUT POWER;AUTO:AUTOTUNE IN PROGRESS;AUTO:AUTOTUNE DONE;SAVE USER;':d.feed(bytes([b]))
  self.assertEqual(d.state['autotune_phase'],'succeeded');self.assertTrue(d.state['autotune_saved'])
  d.feed(b'AUTO;AUTO:WAITING FOR INPUT POWER;AUTOESC;');self.assertEqual(d.state['autotune_phase'],'cancelled');self.assertFalse(d.state['autotune_saved'])
 def test_unknown_never_invents_success(self):
  d=Decoder();d.feed(b'SAVE USER;');self.assertNotIn('autotune_phase',d.state)
  d.feed(b'AUTO:UNRECOGNIZED RESPONSE;SAVE USER;');self.assertEqual(d.state['autotune_phase'],'unknown');self.assertFalse(d.state['autotune_saved'])
 def test_raw_positions_do_not_change_operating_mode(self):
  d=Decoder();d.feed(b'OPERATE;LO2093;TU598;OT-15;AUTO;');self.assertEqual(d.state['status'],'Operate');self.assertEqual(d.state['autotune_load_raw'],2093);self.assertEqual(d.state['autotune_offset_raw'],-15)
 def test_capture_replays(self):
  root=Path(os.environ.get('OM_CAPTURE_DIR',Path.home()/'Downloads'))
  files=[root/('OM3501A-autotune-'+n+'.pcapng') for n in ('success','enter-exit','cancel')]
  if not all(p.exists() for p in files):self.skipTest('Optional local captures absent')
  for path in files[:2]:
   rows=replay(path);phases={r.get('autotune_phase') for r in rows};self.assertTrue({'waiting','tuning','succeeded'}<=phases);self.assertTrue(any(r.get('autotune_saved') for r in rows))
  rows=replay(files[2]);self.assertEqual(rows[-1]['autotune_phase'],'cancelled');self.assertFalse(any(r['transmitting'] for r in rows));self.assertNotIn('succeeded',{r.get('autotune_phase') for r in rows})
 def test_abort_is_latched_and_never_becomes_success(self):
  d=Decoder();d.feed(b'AUTO;AUTO:AUTOTUNE IN PROGRESS;STOP;AUTO:AUTOTUNE ABORTED;AUTO:WAITING FOR INPUT POWER;AUTO:AUTOTUNE DONE;SAVE USER;');self.assertEqual(d.state['autotune_phase'],'stopped-exited');self.assertFalse(d.state['autotune_saved']);d.feed(b'AUTO;');self.assertFalse(d.state['autotune_aborted'])
 def test_stop_capture(self):
  path=Path(os.environ.get('OM_CAPTURE_DIR',Path.home()/'Downloads'))/'OM3501A-autotune-stop.pcapng'
  if not path.exists():self.skipTest('Optional local capture absent')
  rows=replay(path);self.assertEqual(rows[-1]['autotune_phase'],'aborted');self.assertTrue(any(r.get('autotune_phase')=='tuning' for r in rows));self.assertFalse(any(r.get('autotune_phase')=='succeeded' for r in rows))
 def test_rf_release_capture_and_default_exit(self):
  path=Path(os.environ.get('OM_CAPTURE_DIR',Path.home()/'Downloads'))/'OM3501A-autotune-rf-released.pcapng'
  if not path.exists():self.skipTest('Optional local capture absent')
  rows=replay(path);aborts=[r for r in rows if r.get('autotune_phase')=='aborted'];self.assertTrue(aborts);self.assertTrue(all(r['autotune_abort_origin']=='rf_lost' for r in aborts));self.assertEqual(rows[-1]['autotune_phase'],'defaults');self.assertTrue(rows[-1]['autotune_defaults']);self.assertFalse(rows[-1]['autotune_saved']);self.assertFalse(any(r.get('autotune_phase')=='succeeded' for r in rows))

 def test_stop_recovery_capture(self):
  path=Path(os.environ.get('OM_CAPTURE_DIR',Path.home()/'Downloads'))/'OM3501A-autotune-top-recovery.pcapng'
  if not path.exists():self.skipTest('Optional local capture absent')
  rows=replay(path);self.assertEqual(rows[-1]['autotune_phase'],'stopped-exited');self.assertTrue(rows[-1]['autotune_stopped_saved']);self.assertFalse(rows[-1]['autotune_saved']);self.assertFalse(any(r.get('autotune_phase')=='succeeded' for r in rows));self.assertTrue(any(r.get('autotune_abort_origin')=='stop' for r in rows))

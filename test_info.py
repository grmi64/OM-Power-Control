import isolated_settings  # noqa: F401  (keep tests off the real settings file)
import json,time,unittest
from unittest.mock import patch
from decoder import Decoder
from profiles import resolve,profile
from live import Monitor
from session_protocol import ReadOnlySocket

INFO_3501=b'INFO:2401,224 66,0,03.25,355,OM3501A;'
INFO_4001=b'INFO:2302,2204566,2205699,03.42,45,OM4001A;'

class DecoderTests(unittest.TestCase):
 def test_both_reply_layouts_with_fragmentation(self):
  for msg,serial,model,firmware,minutes in ((INFO_3501,'2401','OM3501A','03.25',355),(INFO_4001,'2302','OM4001A','03.42',45)):
   for cut in range(len(msg)+1):
    d=Decoder();d.feed(msg[:cut]);d.feed(msg[cut:]);self.assertEqual(d.state['info'],{'serial':serial,'model':model,'firmware':firmware,'operating_minutes':minutes})
 def test_amplifier_serial_is_kept_but_tube_serials_are_not(self):
  d=Decoder();d.feed(INFO_4001);text=json.dumps(d.state)
  self.assertEqual(d.state['info']['serial'],'2302')
  for tube in ('2204566','2205699'):self.assertNotIn(tube,text)
  d=Decoder();d.feed(INFO_3501);self.assertNotIn('224 66',json.dumps(d.state))
  self.assertEqual(d.state['last_status'],'INFO');self.assertEqual(d.tokens,['INFO:2401,224 66,0,03.25,355,OM3501A'])
 def test_an_unusable_serial_is_left_out_but_the_rest_is_kept(self):
  d=Decoder();d.feed(b'INFO:bad!serial,2,0,03.25,5,OM3501A;');self.assertEqual(d.state['info'],{'model':'OM3501A','firmware':'03.25','operating_minutes':5})
 def test_malformed_replies_are_ignored(self):
  for bad in (b'INFO:1,2,3;',b'INFO:1,2,0,3.2.1,5,OM3501A;',b'INFO:1,2,0,03.25,x,OM3501A;',b'INFO:1,2,0,03.25,5,;',b'INFO:1,2,0,03.25,5,'+b'X'*30+b';'):
   d=Decoder();d.feed(bad);self.assertNotIn('info',d.state,bad)
 def test_info_does_not_disturb_status(self):
  d=Decoder();d.feed(b'ST0100- NO ANTENNA SWITCH;'+INFO_4001+b'TE64;');self.assertEqual(d.state['status'],'Standby');self.assertEqual(d.state['temperature_c'],32)

class ResolveTests(unittest.TestCase):
 def info(self,model,firmware='03.42'):return {'model':model,'firmware':firmware,'operating_minutes':5}
 def test_matching_model_has_no_notice_and_keeps_the_label_profile(self):
  for label,reported in (('OM-3501A','OM3501A'),('om3501a','OM3501A+'),('OM-4001A','OM4001A')):
   p,note=resolve(label,self.info(reported));self.assertEqual(note,'',label);self.assertEqual(p['name'],profile(label)['name'])
 def test_no_reply_changes_nothing(self):
  self.assertEqual(resolve('OM-3501A',None),(profile('OM-3501A'),''))
 def test_a_wrong_label_cannot_unlock_controls_validated_for_another_model(self):
  p,note=resolve('OM-3501A',self.info('OM4001A'))
  self.assertEqual((p['name'],p['controls_verified'],p['full_scale_w']),('OM-4001A',False,5000));self.assertIn('OM4001A',note);self.assertIn('OM-3501A',note)
 def test_a_4001a_label_on_a_3501a_takes_the_3501a_profile(self):
  p,note=resolve('OM-4001A',self.info('OM3501A'));self.assertEqual((p['name'],p['controls_verified']),('OM-3501A',True));self.assertTrue(note)
 def test_unrecognised_reply_keeps_the_label_and_says_so(self):
  p,note=resolve('OM-3501A',self.info('OM4001C'));self.assertEqual(p['name'],'OM-3501A');self.assertIn('does not recognise',note)
  self.assertEqual(resolve('HEXBEAM',self.info('OM4001A'))[0]['name'],'OM-4001A')
 def test_old_firmware_is_flagged(self):
  self.assertIn('older than 3.16',resolve('OM-4001A',self.info('OM4001A','03.10'))[1]);self.assertIn('older than 3.16',resolve('OM-3501A',self.info('OM3501A','02.99'))[1])
  for fw in ('03.16','03.42','04.00'):self.assertEqual(resolve('OM-4001A',self.info('OM4001A',fw))[1],'',fw)
  self.assertEqual(resolve('OM-4001A',self.info('OM4001A','garbage'))[1],'')

class MonitorTests(unittest.TestCase):
 def monitor(self,label,reported=None):
  m=Monitor(simulate=True);m.settings['model']=label;now=time.monotonic()
  m.state={'connection':'Connected','_received':now,'status':'Standby','transmitting':False,'_field_times':{}}
  if reported:m.state['info']={'model':reported,'firmware':'03.42','operating_minutes':5}
  return m
 def test_controls_follow_the_amplifier_not_the_label(self):
  with self.assertRaisesRegex(ValueError,'Monitoring only'):self.monitor('OM-3501A','OM4001A').command('toggle','request-wrong-label',expected_mode='Standby')
  ok=self.monitor('OM-3501A','OM3501A');ok.command('toggle','request-right-label',expected_mode='Standby');self.assertTrue(ok.controls.pending)
  silent=self.monitor('OM-3501A');silent.command('toggle','request-no-reply',expected_mode='Standby');self.assertTrue(silent.controls.pending)
 def test_snapshot_reports_the_effective_profile_and_notice(self):
  s=self.monitor('OM-3501A','OM4001A').snapshot()
  self.assertEqual((s['model_profile']['name'],s['model_profile']['controls_verified'],s['model_profile']['fresh_seconds']),('OM-4001A',False,8));self.assertIn('OM4001A',s['model_notice']);self.assertEqual(s['info']['firmware'],'03.42')
  s=self.monitor('OM-4001A','OM4001A').snapshot();self.assertEqual(s['model_notice'],'')
  self.assertEqual(self.monitor('OM-3501A').snapshot()['model_notice'],'')
 def wait(self,monitor,test,seconds=12):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   snap=monitor.snapshot()
   if test(snap):return snap
   time.sleep(.1)
  self.fail('condition not reached: '+str({k:snap.get(k) for k in ('connection','status','info','error')}))
 def test_each_simulator_identifies_itself_once_per_connection(self):
  for label,model,firmware in (('OM-3501A','OM3501A','03.21'),('OM-4001A','OM4001A','03.42')):
   monitor=Monitor(simulate=True);monitor.settings['model']=label;monitor.connect()
   try:
    s=self.wait(monitor,lambda s:s.get('info') is not None);self.assertEqual((s['info']['model'],s['info']['firmware']),(model,firmware));self.assertEqual(s['model_notice'],'')
    time.sleep(2.5);self.assertEqual(monitor.simulator.sent.count(b'1'),1)
   finally:monitor.disconnect();monitor.thread.join(4)

class Amplifier:
 """Fake amplifier socket for the real worker loop: replies[n] is returned on the nth read after CON,
 and a callable in replies runs (e.g. queues a command) before its bytes are returned."""
 def __init__(self,monitor,replies):self.monitor=monitor;self.replies=list(replies);self.sent=[];self.reads=0
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def settimeout(self,n):pass
 def sendall(self,data):self.sent.append(data)
 def recv(self,n):
  if self.sent.count(b'C')>=2:return b'COFF;'
  self.reads+=1
  if self.reads==1:return b'CON;'
  if not self.replies:self.monitor.stop.set();return b'TE63;'
  reply=self.replies.pop(0)
  return reply() if callable(reply) else reply

class DelayedInfoTests(unittest.TestCase):
 """Review point 2: a command queued under the label's profile must not reach a model the INFO reply rules out."""
 def test_toggle_queued_before_a_late_4001a_info_is_cancelled_not_sent(self):
  # Identification wait already over (INFO very late), so the label's OM-3501A profile accepts the toggle;
  # the INFO reply arrives in the same read and the worker must recheck before sending.
  def queue_then_info():
   m.command('toggle','delayed-info-1',expected_mode='Standby');self.assertTrue(m.controls.pending)
   return INFO_4001
  m=Monitor(allow_hardware=True);m.settings.update(host='192.0.2.1',model='OM-3501A')
  amp=Amplifier(m,[b'ST1100- HEXBEAM;PTTOFF;',queue_then_info,b'TE63;',b'TE63;'])
  with patch('live.socket.create_connection',return_value=amp),patch('live.IDENTIFY_SECONDS',0):m.run()
  self.assertNotIn(b'O',amp.sent);self.assertIsNone(m.controls.pending);self.assertFalse(m.controls.uncertain)
  self.assertIn('monitoring only',m.controls.message)
  self.assertEqual([h['phase'] for h in m.command_history],['queued','cancelled'])
 def test_controls_take_rechecks_the_profile(self):
  from controls import Controls
  now=time.monotonic();s={'connection':'Connected','_received':now,'status':'Standby','transmitting':False,'controls_verified':True}
  for action in ('toggle','on','off'):
   c=Controls();c.request(action,'recheck-'+action,{**s,'status':'Off' if action=='on' else 'Standby'})
   self.assertIsNone(c.take({**s,'status':'Off' if action=='on' else 'Standby','controls_verified':False}));self.assertIsNone(c.pending);self.assertFalse(c.uncertain)
  t={**s,'status':'Operate','autotune_phase':'tuning','transmitting':True};c=Controls();c.request('autotune-stop','recheck-stop',t)
  self.assertIsNone(c.take({**t,'controls_verified':False}))
  with self.assertRaisesRegex(ValueError,'Monitoring only'):Controls().request('toggle','recheck-req',{**s,'controls_verified':False})
 def test_commands_wait_for_identification_then_follow_the_reported_model(self):
  result={}
  def too_early():
   with self.assertRaisesRegex(ValueError,'report its model'):m.command('toggle','too-early-1',expected_mode='Standby')
   result['early']=m.snapshot()['model_pending'];return b'TE63;'
  def after_info():
   m.command('toggle','after-info-1',expected_mode='Standby');return b'TE63;'
  m=Monitor(allow_hardware=True);m.settings.update(host='192.0.2.1',model='OM-3501A')
  amp=Amplifier(m,[b'ST1100- HEXBEAM;PTTOFF;',too_early,INFO_3501,after_info,b'OPERATE;'])
  with patch('live.socket.create_connection',return_value=amp):m.run()
  self.assertTrue(result['early']);self.assertEqual(amp.sent.count(b'O'),1);self.assertEqual(m.controls.message,'Operating mode confirmed by amplifier')
 def test_a_4001a_reply_inside_the_wait_never_unlocks_controls(self):
  def try_toggle():
   with self.assertRaisesRegex(ValueError,'Monitoring only'):m.command('toggle','after-4001-1',expected_mode='Standby')
   return b'TE63;'
  m=Monitor(allow_hardware=True);m.settings.update(host='192.0.2.1',model='OM-3501A')
  amp=Amplifier(m,[b'ST0100- NO ANTENNA SWITCH;PTTOFF;',INFO_4001,try_toggle])
  with patch('live.socket.create_connection',return_value=amp):m.run()
  self.assertNotIn(b'O',amp.sent)
 def test_no_info_reply_falls_back_to_the_label_after_the_wait(self):
  # Firmware that does not answer INFO keeps working once the identification wait has passed.
  def queue():
   m.command('toggle','no-info-1',expected_mode='Standby');return b'TE63;'
  m=Monitor(allow_hardware=True);m.settings.update(host='192.0.2.1',model='OM-3501A')
  amp=Amplifier(m,[b'ST1100- HEXBEAM;PTTOFF;',queue,b'OPERATE;'])
  with patch('live.socket.create_connection',return_value=amp),patch('live.IDENTIFY_SECONDS',0):m.run()
  self.assertEqual(amp.sent.count(b'O'),1);self.assertFalse(m.snapshot()['model_pending'])

class SafetyTests(unittest.TestCase):
 def test_read_only_allows_info_but_no_other_query_or_control(self):
  class Wire:
   def __init__(self):self.sent=[]
   def sendall(self,data):self.sent.append(data)
  wire=Wire();guard=ReadOnlySocket(wire);guard.sendall(b'1');self.assertEqual(wire.sent,[b'1'])
  for data in (b'2',b'3',b'4',b'5',b'G',b'H',b'$',b'%',b'^',b'P',b'N',b'Q',b'K',b'J',b'M',b'L',b'S',b'O',b'Y',b'Z'):
   with self.assertRaises(ValueError):guard.sendall(data)
  self.assertEqual(wire.sent,[b'1'])
if __name__=='__main__':unittest.main()

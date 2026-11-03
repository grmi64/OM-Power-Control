import re,time,unittest
from unittest.mock import patch
from decoder import Decoder
from simulator import Simulated4001A,SimulatedAmplifier,simulator_for
from live import Monitor

class Clock:
 def __init__(self):self.now=1000.0
 def __call__(self):return self.now

def drain(sim):
 with sim.lock:data=bytes(sim.queue);sim.queue.clear()
 return data
def tokens(data):return [t for t in data.decode('ascii').split(';') if t]
def batch(data):return dict(re.findall(r'(IP|UP|UGA|UGB|US|UHA|UHB|UM|TE)(-?[\d.]+)',data.decode('ascii')))

class WireTests(unittest.TestCase):
 def setUp(self):self.clock=Clock();self.sim=Simulated4001A(warmup_seconds=20,cooldown_seconds=30,clock=self.clock)
 def ask(self,data):self.sim.sendall(data);return drain(self.sim)
 def test_session_status_and_frequency(self):
  self.assertEqual(self.ask(b'C'),b'CON;');self.assertEqual(self.ask(b'?'),b'ST0000- NO ANTENNA SWITCH;');self.assertEqual(self.ask(b'F'),b'FR18100;')
 def test_off_telemetry_matches_the_capture(self):
  self.assertEqual(batch(self.ask(b'#')),{'IP':'0','UP':'0','UGA':'139','UGB':'139','US':'0','UHA':'0.0','UHB':'0.0','UM':'244','TE':'68'})
  self.assertEqual(self.ask(b'#')[:0],b'')
 def test_poll_replies_are_throttled_to_about_every_3_2_seconds(self):
  self.assertIn(b'TE68',self.ask(b'#'))
  for _ in range(3):
   self.clock.now+=1.0
   if _<2:self.assertEqual(self.ask(b'#'),b'',_)
  self.clock.now+=0.3;self.assertIn(b'TE68',self.ask(b'#'))
 def test_no_ptt_noise_on_polls(self):
  self.assertNotIn(b'PTTOFF',self.ask(b'#')+self.ask(b'?'))
 def test_warm_up_sequence_and_values(self):
  self.assertEqual(self.ask(b'Y'),b'WA20;');seen=[]
  for _ in range(20):
   self.clock.now+=1.0;self.sim.sendall(b'?');seen+=tokens(drain(self.sim))
  waits=[int(t[2:]) for t in seen if re.fullmatch(r'WA\d+',t)]
  self.assertEqual(waits,list(range(19,0,-1)));i=seen.index('PTTOFF');self.assertEqual(seen[i:i+3],['PTTOFF','PAON','STBY'])
  self.assertEqual(tokens(self.ask(b'?'))[-1],'ST0100- NO ANTENNA SWITCH')
 def test_batch_values_through_warm_up_and_standby(self):
  self.ask(b'Y');self.clock.now+=10.0;mid=batch(self.ask(b'#'))
  self.assertEqual((mid['US'],mid['UGA'],mid['UGB']),('19','128','128'));self.assertTrue(1500<int(mid['UP'])<1700);self.assertTrue(8.0<=float(mid['UHA'])<=8.9)
  self.clock.now+=11.0;done=batch(self.ask(b'#'))
  self.assertEqual((done['US'],done['UGA'],done['UGB'],done['UHA']),('19','140','141','9.0'));self.assertTrue(3200<int(done['UP'])<3300)
 def test_operate_toggle_only_when_fully_on(self):
  self.assertEqual(self.ask(b'O'),b'');self.ask(b'Y');self.clock.now+=5;reply=self.ask(b'O');self.assertNotIn(b'OPERATE',reply);self.assertNotIn(b'STBY',reply)
  self.clock.now+=20;self.ask(b'?');self.assertEqual(self.ask(b'O'),b'OPERATE;');self.assertEqual(self.ask(b'?'),b'ST0110- NO ANTENNA SWITCH;');self.assertEqual(self.ask(b'O'),b'STBY;')
 def test_cooling_reports_temperature_then_off(self):
  self.sim.set_power(True);self.clock.now+=25;self.ask(b'?');self.assertEqual(self.sim.mode,'Standby')
  self.assertEqual(self.ask(b'Z'),b'COON;');temps=[]
  for _ in range(30):
   self.clock.now+=1.0;self.sim.sendall(b'?');temps+=[int(t[2:]) for t in tokens(drain(self.sim)) if re.fullmatch(r'CT\d+',t)]
  self.assertEqual(self.sim.mode,'Off');self.assertTrue(temps and all(t>40 for t in temps) and temps==sorted(temps,reverse=True))
 def test_off_commands_are_ignored_when_already_in_that_state(self):
  self.sim.set_power(False);self.assertEqual(self.sim.mode,'Off');self.ask(b'Z');self.assertEqual(self.sim.mode,'Off')
  self.sim.set_power(True);self.sim.set_power(True);self.assertEqual(self.sim.mode,'Warming up')
 def test_injected_alerts(self):
  for token in ('WG11','FA4','HF','HVF','FERROR','WG15'):self.sim.inject(token);self.assertEqual(drain(self.sim),token.encode()+b';')
  self.sim.inject('CLEAR');self.assertEqual(drain(self.sim),b'')
  for token in ('WG0','WG16','XX','HF;ST0000',None,11):
   with self.assertRaises(ValueError):self.sim.inject(token)
 def test_hard_fault_repeats_every_second_until_cleared(self):
  self.sim.inject('HF');self.assertEqual(drain(self.sim),b'HF;')
  for _ in range(3):
   self.clock.now+=1.0;self.sim.sendall(b'?');self.assertIn(b'HF;',drain(self.sim))
  self.clock.now+=0.4;self.sim.sendall(b'?');self.assertNotIn(b'HF;',drain(self.sim))
  self.sim.inject('CLEAR');self.assertEqual(drain(self.sim),b'')
  self.clock.now+=5.0;self.sim.sendall(b'?');self.assertNotIn(b'HF;',drain(self.sim))
  self.sim.inject('HVF');self.clock.now+=5.0;self.sim.sendall(b'?');self.assertEqual(drain(self.sim).count(b'HVF'),1)
 def test_decoder_follows_the_whole_session(self):
  d=Decoder();status=[]
  for command,advance in ((b'C',0),(b'?',0),(b'Y',0)):self.sim.sendall(command);d.feed(drain(self.sim));status.append(d.state.get('status'))
  for _ in range(21):
   self.clock.now+=1.0;self.sim.sendall(b'#');self.sim.sendall(b'?');d.feed(drain(self.sim));status.append(d.state['status'])
  self.assertEqual((status[1],status[2],status[-1]),('Off','Warming up','Standby'));self.assertIn('Warming up',status)
  self.assertEqual((d.state['grid_a_v'],d.state['grid_b_v'],d.state['screen_v']),(140.0,141.0,19.0))

class SelectionTests(unittest.TestCase):
 def test_simulator_for_model(self):
  for model in ('OM-4001A','om4001a'):self.assertIsInstance(simulator_for(model),Simulated4001A)
  for model in ('OM-3501A','OM-9999','',None):self.assertIs(type(simulator_for(model)),SimulatedAmplifier)
 def test_3501a_simulator_has_no_extra_controls(self):
  sim=SimulatedAmplifier();self.assertEqual(sim.FEATURES,())
  with self.assertRaises(ValueError):sim.set_power(True)
  with self.assertRaises(ValueError):sim.inject('HF')

class MonitorTests(unittest.TestCase):
 def wait(self,monitor,test,seconds=12):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   snap=monitor.snapshot()
   if test(snap):return snap
   time.sleep(.1)
  self.fail('condition not reached; last state: '+str({k:snap.get(k) for k in ('connection','status','screen_v','grid_a_v','error')}))
 def test_monitor_shows_off_warm_up_and_standby_with_the_vendor_display_rules(self):
  with patch('simulator.simulator_for',return_value=Simulated4001A(warmup_seconds=5)):
   monitor=Monitor(simulate=True);monitor.settings['model']='OM-4001A';monitor.connect()
   try:
    off=self.wait(monitor,lambda s:s['connection']=='Connected' and s.get('status')=='Off' and s.get('grid_a_v') is not None)
    self.assertEqual((off['grid_a_v'],off['grid_b_v']),(0.0,0.0));self.assertEqual(off['sim_features'],['power','alert']);self.assertEqual(off['model_profile']['name'],'OM-4001A')
    monitor.simulator.set_power(True)
    warm=self.wait(monitor,lambda s:s.get('status')=='Warming up' and s.get('screen_v') is not None);self.assertEqual(warm['screen_v'],0.0)
    ready=self.wait(monitor,lambda s:s.get('status')=='Standby' and s.get('screen_v')==19.0 and s.get('grid_b_v')==-141.0)
    self.assertEqual(ready['connection'],'Connected');self.assertEqual(ready['grid_b_v'],-141.0)
    monitor.simulator.inject('WG11');alert=self.wait(monitor,lambda s:s.get('alert'));self.assertEqual(alert['alert']['kind'],'warning')
   finally:monitor.disconnect();monitor.thread.join(4)
 def test_3501a_monitor_reports_no_simulator_extras(self):
  monitor=Monitor(simulate=True);monitor.settings['model']='OM-3501A';monitor.simulator=simulator_for('OM-3501A');self.assertEqual(monitor.snapshot()['sim_features'],[])
class ModelOptionTests(unittest.TestCase):
 def test_simulation_model_option(self):
  from live import simulation_model
  cur={'host':'simulation','port':10001,'model':'OM-3501A','callsign':'','auto_connect':False,'secondary_measurement':'reflected','share_dxc':False}
  self.assertEqual(simulation_model('om-4001a',False,cur),'OM-4001A');self.assertEqual(simulation_model('OM-3501A',False,cur),'OM-3501A')
  with self.assertRaises(ValueError):simulation_model('OM-4001A',True,cur)
  with self.assertRaises(ValueError):simulation_model('x'*41,False,cur)
  with self.assertRaises(ValueError):simulation_model('',False,cur)
 def test_extra_simulator_controls_stay_hidden_when_unsupported(self):
  from pathlib import Path
  html=Path(__file__).with_name('live.html').read_text(encoding='utf-8')
  # connectRow sets display:flex, which would override the hidden attribute without this rule.
  self.assertLess(html.index('.connectRow[hidden]{display:none}'),html.index('.connectRow{display:flex'))
  self.assertIn('id="simExtras" hidden',html)
if __name__=='__main__':unittest.main()

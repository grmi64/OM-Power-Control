import json,os,tempfile,time,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
from live import Monitor
from dxc_feed import start
class FeedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'OM_SETTINGS_PATH':str(Path(self.tmp.name)/'settings.json')});self.env.start();self.m=Monitor()
  self.m.state={'connection':'Connected','status':'Standby','_received':time.monotonic(),'transmitting':False}
  self.m.settings.update(host='192.0.2.1',callsign='W1AW')
  self.server=start(self.m,0);self.base='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):self.server.shutdown();self.server.server_close();self.env.stop();self.tmp.cleanup()
 def get(self,headers=None):return urllib.request.urlopen(urllib.request.Request(self.base+'/api/v1/telemetry',headers=headers or {}))
 def enable(self):self.m.configure({**self.m.settings,'share_dxc':True})
 def test_opt_in_and_private_fields_not_shared(self):
  with self.assertRaises(urllib.error.HTTPError) as err:self.get()
  self.assertEqual(err.exception.code,403);self.enable()
  with self.get() as response:
   data=json.load(response);self.assertIsNone(response.headers.get('Access-Control-Allow-Origin'))
  self.assertEqual(data['model'],'OM Power Control');self.assertEqual(data['status'],'live')
  self.assertNotIn('192.0.2.1',json.dumps(data));self.assertNotIn('W1AW',json.dumps(data));self.assertNotIn('raw',data['om'])
  for headers in ({'Origin':'https://foreign.test'},{'Host':'foreign.test'}):
   with self.assertRaises(urllib.error.HTTPError):self.get(headers)
 def test_saved_measurement_is_shared_and_changes_without_reconnect(self):
  self.enable()
  for choice in ('input','plate_a','gain_db','reflected'):
   self.m.configure_display({'secondary_measurement':choice})
   self.assertEqual(json.load(self.get())['om']['settings']['secondary_measurement'],choice)
 def post(self,token,value):return urllib.request.urlopen(urllib.request.Request(self.base+'/api/v1/control',json.dumps(value).encode(),headers={'X-OM-Feed-Token':token,'Content-Type':'application/json'}))
 def test_existing_controls_guard_and_single_request(self):
  self.enable();token=json.load(self.get())['control_token'];value={'action':'toggle','id':'request-test-123','expected_mode':'Standby'}
  with self.assertRaises(urllib.error.HTTPError):self.post('wrong',value)
  self.assertIsNone(self.m.controls.pending)
  self.post(token,value).close();pending=self.m.controls.pending;self.post(token,value).close();self.assertIs(self.m.controls.pending,pending)
  self.assertEqual(self.m.snapshot()['command_history'][-1]['phase'],'duplicate ignored');self.assertEqual(self.m.snapshot()['command_history'][-1]['source'],'DXC')
  self.assertIsNone(self.m.thread,'Sharing must never create another amplifier reader')
  self.m.controls.pending=None;self.m.state['transmitting']=True
  with self.assertRaises(urllib.error.HTTPError):self.post(token,{**value,'id':'rf-request-456'})
  self.assertIsNone(self.m.controls.pending)
  self.m.settings['share_dxc']=False
  with self.assertRaises(urllib.error.HTTPError):self.post(token,value)

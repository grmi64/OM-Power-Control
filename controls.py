"""Single outstanding, non-retrying commands owned by the socket worker."""
import time
COMMANDS={'toggle':(b'O',{'OPERATE','STBY'}),'on':(b'Y',{'PAON','WA'}),'off':(b'Z',{'PAOFF','COON','CO'})}
class Controls:
 def __init__(self):self.pending=None;self.message='';self.uncertain=False;self.seen=set();self.last_sent=float('-inf')
 def request(self,action,key,state,expected_mode=None):
  now=time.monotonic()
  if action not in COMMANDS:raise ValueError('Unknown control')
  if not isinstance(key,str) or not 8<=len(key)<=100:raise ValueError('Invalid request identifier')
  if key in self.seen:return
  if self.pending or self.uncertain:raise ValueError('Wait for confirmation; reconnect after an unconfirmed result')
  if state.get('connection')!='Connected' or now-state.get('_received',0)>3:raise ValueError('Fresh amplifier communication is required')
  if state.get('transmitting'):raise ValueError('Stop transmission before changing amplifier state')
  status=state.get('status','Unknown')
  if expected_mode is not None and (action!='toggle' or expected_mode not in ('Operate','Standby') or status!=expected_mode):raise ValueError('Amplifier mode changed; review the updated button before trying again')
  if status in ('Cooling down','Warming up'):raise ValueError('Wait for the amplifier countdown to finish')
  if action=='toggle' and status=='Off':raise ValueError('Turn the amplifier on first')
  if action=='on' and status in ('On','Operate','Standby'):raise ValueError('Amplifier is already on')
  if action=='off' and status=='Off':raise ValueError('Amplifier is already off')
  if now-self.last_sent<2:raise ValueError('Please wait before sending another command')
  self.seen.add(key)
  if len(self.seen)>1000:raise ValueError('Reconnect before sending additional commands')
  self.pending={'action':action,'sent':None,'expected_mode':expected_mode};self.message='Command queued'
 def take(self,state):
  if not self.pending or self.pending['sent'] is not None:return None
  reason=None
  if state.get('transmitting'):reason='amplifier is transmitting'
  elif state.get('connection')!='Connected' or time.monotonic()-state.get('_received',0)>3:reason='fresh amplifier data is unavailable'
  elif state.get('status') in ('Cooling down','Warming up'):reason='amplifier countdown is active'
  elif self.pending['action']=='on' and state.get('status') in ('On','Operate','Standby'):reason='amplifier is already on'
  elif self.pending['action']=='off' and state.get('status')=='Off':reason='amplifier is already off'
  elif self.pending['action']=='toggle' and state.get('status')=='Off':reason='amplifier is off'
  elif self.pending.get('expected_mode') and state.get('status')!=self.pending['expected_mode']:reason='amplifier mode changed'
  if reason:
   self.pending=None;self.message='Command cancelled: '+reason;return None
  self.pending['sent']=time.monotonic();self.last_sent=self.pending['sent'];self.message='Sent once; waiting for amplifier confirmation'
  return COMMANDS[self.pending['action']][0]
 def observe(self,tokens):
  if not self.pending or self.pending['sent'] is None:return
  wanted=COMMANDS[self.pending['action']][1]
  if any(t in wanted or (t.startswith('WA') and 'WA' in wanted and t[2:].isdigit()) or (t.startswith('CO') and 'CO' in wanted and t[2:].isdigit()) for t in tokens):
   action=self.pending['action']
   expected=self.pending.get('expected_mode')
   if action=='toggle' and expected:
    target='STBY' if expected=='Operate' else 'OPERATE'
    mode_tokens=[t for t in tokens if t in ('STBY','OPERATE')]
    if not mode_tokens or mode_tokens[-1]!=target:
     self.pending=None;self.uncertain=True;self.message='Amplifier reported a different mode than requested. No retry was sent.';return
   self.pending=None;self.message={'toggle':'Operating mode confirmed by amplifier','on':'Power-on accepted by amplifier','off':'Shutdown accepted by amplifier'}[action]
 def tick(self):
  if self.pending and self.pending['sent'] is not None and time.monotonic()-self.pending['sent']>5:
   self.pending=None;self.uncertain=True;self.message='No command confirmation. It may have taken effect; no retry was sent. Reconnect to reassess.'
 def lost(self):
  if self.pending:
   sent=self.pending['sent'] is not None;self.pending=None;self.uncertain=sent;self.message='Connection lost; command result unknown. No retry was sent.' if sent else 'Unsent command cancelled'
 def view(self):return {'pending':self.pending is not None,'pending_action':self.pending['action'] if self.pending else None,'cooldown_remaining':max(0,round(2-(time.monotonic()-self.last_sent),2)),'uncertain':self.uncertain,'message':self.message}

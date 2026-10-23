"""Single outstanding, non-retrying commands owned by the socket worker."""
import time
COMMANDS={'toggle':(b'O',{'OPERATE','STBY'}),'on':(b'Y',{'PAON','WA'}),'off':(b'Z',{'PAOFF','COON','CO'}),'autotune':(b'L',{'AUTO'}),'autotune-exit':(b'*',{'AUTOESC','SAVE DEFAULT'}),'autotune-stop':(b'8',{'STOP','AUTO:AUTOTUNE ABORTED'})}
ACTIVE_TUNE={'entered','waiting','tuning','unknown','aborted'}
def tune_guard(action,state,stage=0):
 phase=state.get('autotune_phase')
 if action=='autotune':
  if state.get('status')!='Operate':return 'Select Operate before starting automatic tuning'
  if (stage==0 and phase in ACTIVE_TUNE) or (stage==1 and phase not in ('entered','waiting')):return 'Automatic tuning state changed; review the amplifier'
 elif action=='autotune-stop':
  if phase!='tuning':return 'Stop is verified only during active automatic tuning'
 elif action=='autotune-exit':
  if phase!='waiting' and not (phase=='aborted' and state.get('autotune_abort_origin') in ('rf_lost','stop')):return 'Exit is verified while waiting or after an RF-interrupted tune; check amplifier after Stop'
 elif phase in ACTIVE_TUNE:return 'Automatic tuning is active or unrecognized; exit the waiting state before other controls'
 return None

class Controls:
 def __init__(self):self.pending=None;self.message='';self.uncertain=False;self.seen=set();self.last_sent=float('-inf')
 def request(self,action,key,state,expected_mode=None):
  now=time.monotonic()
  if action not in COMMANDS:raise ValueError('Unknown control')
  if not isinstance(key,str) or not 8<=len(key)<=100:raise ValueError('Invalid request identifier')
  if key in self.seen:return
  if self.pending or self.uncertain:raise ValueError('Wait for confirmation; reconnect after an unconfirmed result')
  if state.get('connection')!='Connected' or now-state.get('_received',0)>3:raise ValueError('Fresh amplifier communication is required')
  if state.get('transmitting') and action!='autotune-stop':raise ValueError('Stop transmission before changing amplifier state')
  reason=tune_guard(action,state)
  if reason:raise ValueError(reason)
  status=state.get('status','Unknown')
  if expected_mode is not None and (action!='toggle' or expected_mode not in ('Operate','Standby') or status!=expected_mode):raise ValueError('Amplifier mode changed; review the updated button before trying again')
  if status in ('Cooling down','Warming up'):raise ValueError('Wait for the amplifier countdown to finish')
  if action=='toggle' and status=='Off':raise ValueError('Turn the amplifier on first')
  if action=='on' and status in ('On','Operate','Standby'):raise ValueError('Amplifier is already on')
  if action=='off' and status=='Off':raise ValueError('Amplifier is already off')
  if action!='autotune-stop' and now-self.last_sent<2:raise ValueError('Please wait before sending another command')
  self.seen.add(key)
  if len(self.seen)>1000:raise ValueError('Reconnect before sending additional commands')
  self.pending={'id':key,'action':action,'sent':None,'expected_mode':expected_mode,'exit_after_rf_abort':action=='autotune-exit' and state.get('autotune_phase')=='aborted','exit_abort_origin':state.get('autotune_abort_origin') if action=='autotune-exit' and state.get('autotune_phase')=='aborted' else None};self.message='Command queued'
 def take(self,state):
  if not self.pending or self.pending['sent'] is not None:return None
  reason=None
  if state.get('transmitting') and self.pending['action']!='autotune-stop':reason='amplifier is transmitting'
  elif state.get('connection')!='Connected' or time.monotonic()-state.get('_received',0)>3:reason='fresh amplifier data is unavailable'
  elif state.get('status') in ('Cooling down','Warming up'):reason='amplifier countdown is active'
  elif self.pending['action']=='on' and state.get('status') in ('On','Operate','Standby'):reason='amplifier is already on'
  elif self.pending['action']=='off' and state.get('status')=='Off':reason='amplifier is already off'
  elif self.pending['action']=='toggle' and state.get('status')=='Off':reason='amplifier is off'
  elif self.pending.get('expected_mode') and state.get('status')!=self.pending['expected_mode']:reason='amplifier mode changed'
  if not reason and self.pending['action']=='autotune-exit' and self.pending.get('exit_abort_origin') and state.get('autotune_abort_origin')!=self.pending['exit_abort_origin']:reason='tuning abort state changed'
  if not reason:reason=tune_guard(self.pending['action'],state,self.pending.get('stage',0))
  if reason:
   self.pending=None;self.message='Command cancelled: '+reason;return None
  self.pending['ever_sent']=True;self.pending['sent']=time.monotonic();self.last_sent=self.pending['sent'];self.message='Sent once; waiting for amplifier confirmation'
  return b'&' if self.pending['action']=='autotune' and self.pending.get('stage')==1 else COMMANDS[self.pending['action']][0]
 def observe(self,tokens):
  if not self.pending or self.pending['sent'] is None:return
  action=self.pending['action']
  if action=='autotune':
   if self.pending.get('stage',0)==0 and 'AUTO' in tokens:
    self.pending.update(stage=1,sent=None);self.message='Automatic mode acknowledged; preparing tuning';return
   if self.pending.get('stage')==1 and 'AUTO:WAITING FOR INPUT POWER' in tokens:
    self.pending=None;self.message='Automatic tuning ready; operator supplies tuning RF';return
   if any(t.startswith('AUTO') for t in tokens):
    self.pending=None;self.uncertain=True;self.message='Unexpected automatic-tuning response. Check amplifier; no retry was sent.'
   return
  wanted=({'SAVE USER','SAVE DEFAULT'} if self.pending.get('exit_abort_origin')=='stop' else {'SAVE DEFAULT'} if self.pending.get('exit_after_rf_abort') else {'AUTOESC'}) if action=='autotune-exit' else COMMANDS[action][1]
  if any(t in wanted or (t.startswith('WA') and 'WA' in wanted and t[2:].isdigit()) or (t.startswith('CO') and 'CO' in wanted and t[2:].isdigit()) for t in tokens):
   action=self.pending['action']
   expected=self.pending.get('expected_mode')
   if action=='toggle' and expected:
    target='STBY' if expected=='Operate' else 'OPERATE'
    mode_tokens=[t for t in tokens if t in ('STBY','OPERATE')]
    if not mode_tokens or mode_tokens[-1]!=target:
     self.pending=None;self.uncertain=True;self.message='Amplifier reported a different mode than requested. No retry was sent.';return
   defaults=action=='autotune-exit' and self.pending.get('exit_after_rf_abort')
   stopped_saved=defaults and self.pending.get('exit_abort_origin')=='stop' and 'SAVE USER' in tokens
   self.pending=None;self.message={'toggle':'Operating mode confirmed by amplifier','on':'Power-on accepted by amplifier','off':'Shutdown accepted by amplifier','autotune-exit':'Automatic tuning exit confirmed','autotune-stop':'Auto-tune stopped by amplifier; stop RF manually'}[action]
   if defaults:self.message='Stopped tune exited; amplifier reported user settings saved, not successful tuning' if stopped_saved else 'Auto-tune exited; amplifier reported default settings saved'
 def tick(self):
  if self.pending and self.pending['sent'] is not None and time.monotonic()-self.pending['sent']>5:
   self.pending=None;self.uncertain=True;self.message='No command confirmation. It may have taken effect; no retry was sent. Reconnect to reassess.'
 def lost(self):
  if self.pending:
   sent=self.pending.get('ever_sent',self.pending['sent'] is not None);self.pending=None;self.uncertain=sent;self.message='Connection lost; command result unknown. No retry was sent.' if sent else 'Unsent command cancelled'
 def view(self):return {'pending':self.pending is not None,'pending_action':self.pending['action'] if self.pending else None,'cooldown_remaining':max(0,round(2-(time.monotonic()-self.last_sent),2)),'uncertain':self.uncertain,'message':self.message}

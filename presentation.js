/* Presentation only: never writes amplifier state or issues commands. */
function amplifierPresentation(s) {
 const connection=s.connection||'Disconnected';
 if(connection==='Disconnecting')return {kind:'waiting',title:'Disconnecting',detail:'Closing amplifier communication session'};
 if(connection==='Connecting'||connection==='Waiting for amplifier data')return {kind:'waiting',title:'Connecting',detail:connection==='Connecting'?'Opening amplifier connection':'Waiting for amplifier response'};
 if(connection==='Stale')return {kind:'stale',title:'Readings delayed',detail:'Waiting for fresh amplifier data · controls paused'};
 if(connection!=='Connected')return {kind:'offline',title:'Disconnected',detail:'Amplifier state unavailable'};
 const mode=s.status||'Unknown';
 if(mode==='Warming up'||mode==='Cooling down') {
  const n=Number.isInteger(s.countdown)&&s.countdown>=0?s.countdown:null;
  const remaining=n===null?'Waiting for amplifier countdown':Math.floor(n/60)+':'+String(n%60).padStart(2,'0')+' remaining';
  return {kind:mode==='Warming up'?'warming':'cooling',title:mode,detail:remaining+' · reported by amplifier'};
 }
 if(s.transmitting===true)return {kind:'transmitting',title:'Transmitting',detail:mode==='Operate'?'Operate · RF active':'RF active · mode awaiting confirmation'};
 if(mode==='Operate')return {kind:'operate',title:'Operate',detail:'Amplifier enabled · no transmit indication'};
 if(mode==='Standby')return {kind:'standby',title:'Standby',detail:'Amplifier in standby'};
 if(mode==='Off')return {kind:'off',title:'Amplifier off',detail:'Network listener connected'};
 return {kind:'waiting',title:'Awaiting mode confirmation',detail:mode==='On'?'Powered on · waiting for operating mode':'Connected · operating mode not yet reported'};
}
if(typeof module!=='undefined')module.exports={amplifierPresentation};

function amplifierControls(s,localPending=false){
 const mode=s.status||'Unknown',c=s.control||{};
 let reason='';
 if(s.settings?.model&&s.settings.model!=='OM-3501A')reason='Monitoring only: controls are unverified for this model.';
 else if(s.connection!=='Connected'||s.age_seconds>3)reason='Connect and wait for fresh amplifier data to use controls.';
 else if(c.uncertain)reason='Command result is uncertain. Reconnect to reassess; no retry was sent.';
 else if(localPending||c.pending)reason='Waiting for amplifier confirmation…';
 else if(['entered','waiting','tuning','unknown','aborted'].includes(s.autotune_phase))reason='Automatic tuning active; use its controls below.';
 else if(s.transmitting)reason='Stop transmission before changing amplifier state.';
 else if(mode==='Cooling down'||mode==='Warming up')reason='Wait for the amplifier countdown to finish.';
 else if(c.cooldown_remaining>0)reason='Waiting briefly before another command.';
 const disabled=!!reason;
 return {reason,
  toggle:{label:mode==='Operate'?'Go to Standby':mode==='Standby'?'Go to Operate':'Toggle Operate / Standby',disabled:disabled||mode==='Off',expectedMode:['Operate','Standby'].includes(mode)?mode:null},
  on:{label:'Power on',disabled:disabled||['On','Operate','Standby'].includes(mode)},
  off:{label:'Power off',disabled:disabled||mode==='Off'}
 };
}
if(typeof module!=='undefined')module.exports.amplifierControls=amplifierControls;

function amplifierConnection(s){
 const endpoint=s.settings?String(s.settings.host)+':'+String(s.settings.port):'';
 let state=s.connection||'Disconnected';
 if(state==='Connected'&&s.age_seconds>3)state='Stale';
 let result={endpoint,kind:'offline',badge:'OFFLINE',label:'Disconnected',detail:'No amplifier connection',error:''};
 if(state==='Connected')result={...result,kind:'live',badge:'LIVE',label:'Connected',detail:'Receiving amplifier data'};
 else if(state==='Disconnecting')result={...result,kind:'waiting',badge:'CLOSING',label:'Disconnecting',detail:'Closing amplifier communication session'};
 else if(state==='Connecting')result={...result,kind:'waiting',badge:'CONNECTING',label:'Connecting',detail:'Opening amplifier connection'};
 else if(state==='Waiting for amplifier data')result={...result,kind:'waiting',badge:'WAITING',label:'Waiting for data',detail:'Connected to the listener; waiting for amplifier data'};
 else if(state==='Stale')result={...result,kind:'stale',badge:'DELAYED',label:'Data delayed',detail:'Fresh amplifier data is delayed; operating controls are paused'};
 if(s.error){
  const raw=String(s.error);
  result.error=raw.includes('No connection acknowledgement')?'Amplifier did not acknowledge the connection. Try Connect again.':raw.includes('No route to host')?'Cannot reach the amplifier. Check its network connection and address.':raw.includes('No amplifier data for 10 seconds')?'No amplifier data for 10 seconds. The connection was closed.':raw.includes('refused')?'Connection refused. Check the amplifier address and port.':raw;
  result.detail=result.error;
 }
 return result;
}
if(typeof module!=='undefined')module.exports.amplifierConnection=amplifierConnection;

// The gradient occupies the entire fixed 3500 W track. Reveal it without rescaling its colors.
function forwardPowerClip(watts){const value=typeof watts==='number'&&Number.isFinite(watts)?Math.max(0,Math.min(3500,watts)):0;return 'inset(0 '+(100-value/3500*100).toFixed(3)+'% 0 0)'}
if(typeof module!=='undefined')module.exports.forwardPowerClip=forwardPowerClip;

// Both readings describe the same mismatch. Color only fresh, active RF data.
function mismatchColor(s){
 const neutral='#a5b2b6';
 if(s.connection!=='Connected'||s.age_seconds>3||s.transmitting!==true||
    !Number.isFinite(s.forward)||s.forward<=0||!Number.isFinite(s.reflected)||s.reflected<0||
    !Number.isFinite(s.swr)||s.swr<1)return neutral;
 const stops=[[1,[121,213,179]],[1.5,[241,187,103]],[2,[229,103,88]]];
 const value=Math.min(2,s.swr),i=value<=1.5?0:1;
 const [low,a]=stops[i],[high,b]=stops[i+1],t=(value-low)/(high-low);
 return 'rgb('+a.map((v,j)=>Math.round(v+(b[j]-v)*t)).join(', ')+')';
}
if(typeof module!=='undefined')module.exports.mismatchColor=mismatchColor;

// Model profile: keep the monitored parameter separate from its visual meter.
const OM3501A_PROFILE=Object.freeze({key:'screen_ma',label:'Screen current · Iscreen',unit:'mA',min:-60,max:60});
function auxiliaryMeter(s,profile=OM3501A_PROFILE){
 const value=s[profile.key],valid=s.connection==='Connected'&&!(s.age_seconds>3)&&typeof value==='number'&&Number.isFinite(value);
 const position=valid?100*(Math.max(profile.min,Math.min(profile.max,value))-profile.min)/(profile.max-profile.min):50;
 return {label:profile.label,unit:profile.unit,value:valid?value:null,position,min:profile.min,max:profile.max};
}
if(typeof module!=='undefined')module.exports.auxiliaryMeter=auxiliaryMeter;

// Display ranges, not amplifier operating limits. Numeric values remain unclipped.
const SECONDARY_PROFILES=Object.freeze({
 reflected:{label:'Reflected',menu:'Reflected power (Preflect)',unit:'W',max:500,digits:0},
 input:{label:'Input power',menu:'Input power (Pinput)',unit:'W',max:100,digits:0},
 plate_a:{label:'Plate current',menu:'Anode (plate) current (Iplate)',unit:'A',max:3,digits:2},
 gain_db:{label:'Calc gain',menu:'Calculated gain',unit:'dB',max:30,digits:1}
});
function secondaryMeter(s,key='reflected'){
 if(!Object.hasOwn(SECONDARY_PROFILES,key))key='reflected';
 const p=SECONDARY_PROFILES[key],v=s[key];
 const valid=s.connection==='Connected'&&!(s.age_seconds>3)&&typeof v==='number'&&Number.isFinite(v);
 const value=valid?v:null,position=value===null?0:100*Math.max(0,Math.min(p.max,value))/p.max;
 return {...p,key,value,position,ticks:[0,p.max/2,p.max],color:key==='reflected'?mismatchColor(s):value===null?'#a5b2b6':'#79d5b3'};
}
if(typeof module!=='undefined'){module.exports.secondaryMeter=secondaryMeter;module.exports.SECONDARY_PROFILES=SECONDARY_PROFILES;}

function autotunePresentation(s,pending=false){
 const phase=s.autotune_phase||'idle',active=['entered','waiting','tuning','unknown','aborted'].includes(phase),link=s.connection==='Connected'&&!(s.age_seconds>3);
 let reason='';if(s.settings?.model!=='OM-3501A')reason='Auto-tune is verified only for OM-3501A.';else if(!link)reason='Fresh amplifier communication is required.';else if(pending||s.control?.pending)reason='Waiting for command confirmation.';else if(s.control?.uncertain)reason='Command result uncertain; check amplifier. No retry was sent.';else if(s.transmitting)reason='Stop RF before using tuning controls.';else if(s.control?.cooldown_remaining>0)reason='Please wait before another command.';
 let title={idle:'Automatic tuning',entered:'Preparing auto-tune',waiting:'WAITING FOR INPUT POWER',tuning:'AUTO-TUNE IN PROGRESS',succeeded:'SUCCESSFUL AUTOTUNE!',cancelled:'Auto-tune exited',aborted:'AUTO-TUNE ABORTED',defaults:'Auto-tune exited · defaults restored','stopped-exited':'Stopped tune exited · settings saved',unknown:'Unexpected auto-tune response'}[phase]||'Unexpected auto-tune response';
 let detail={idle:'Operator sets tuning power and supplies the steady carrier.',entered:'Waiting for amplifier readiness.',waiting:'Set the prescribed tuning drive level, then transmit a steady carrier from your radio.',tuning:'Operator controls RF. Stop RF manually if tuning is abnormal.',succeeded:s.autotune_saved?'Amplifier reported settings saved automatically. Stop tuning RF.':'Amplifier reported tuning complete. Stop tuning RF.',cancelled:'Returned from automatic tuning without applying RF.',aborted:s.autotune_abort_origin==='rf_lost'?'RF was released before completion. Exit auto-tune to restore default settings; this was not a successful tune.':s.autotune_abort_origin==='stop'?'Tuning was stopped. Release RF, then use Exit; the amplifier may save its current settings. This is not a successful tune.':'Stop RF manually and check the amplifier. The abort cause is unrecognized.',defaults:'Amplifier reported default settings saved. No successful tune was saved.','stopped-exited':'Amplifier reported user settings saved after Stop. Successful tuning was not confirmed.',unknown:(s.autotune_message||'Unrecognized response')+' · Stop RF and check the amplifier; no retry is sent.'}[phase];
 if(active&&!link){title='Auto-tune result unknown';detail='Communication interrupted. Stop RF manually and check the amplifier.';}
 else if(active&&s.autotune_age_seconds>15){title='Auto-tune status delayed';detail='No recent tuning status. Stop RF manually and check the amplifier; no retry is sent.';}
 const stopBlocked=s.settings?.model!=='OM-3501A'||!link||pending||s.control?.pending||s.control?.uncertain||phase!=='tuning';
 return {stopDisabled:!!stopBlocked,phase,title,detail,visible:phase!=='idle',startDisabled:!!reason||active||s.status!=='Operate',exitDisabled:!!reason||(phase!=='waiting'&&!(phase==='aborted'&&['rf_lost','stop'].includes(s.autotune_abort_origin))),reason};
}
if(typeof module!=='undefined')module.exports.autotunePresentation=autotunePresentation;

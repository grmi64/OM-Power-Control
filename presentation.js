/* Presentation only: never writes amplifier state or issues commands. */
/* Seconds without data before the link counts as delayed; the model profile may allow longer (profiles.py). */
function freshSeconds(s){const v=s&&s.model_profile&&s.model_profile.fresh_seconds;return v>0?v:3}
if(typeof module!=='undefined')module.exports={freshSeconds};
function amplifierPresentation(s) {
 const connection=s.connection||'Disconnected';
 if(connection==='Disconnecting')return {kind:'waiting',title:'Disconnecting',detail:'Closing amplifier communication session'};
 if(connection==='Connecting'||connection==='Waiting for amplifier data')return {kind:'waiting',title:'Connecting',detail:connection==='Connecting'?(s.connect_note||'Opening amplifier connection'):'Waiting for amplifier response'};
 if(connection==='Stale')return {kind:'stale',title:'Readings delayed',detail:'Waiting for fresh amplifier data · controls paused'};
 if(connection!=='Connected')return {kind:'offline',title:'Disconnected',detail:'Amplifier state unavailable'};
 const mode=s.status||'Unknown';
 if(s.fault)return {kind:'fault',title:s.fault.kind==='hv_fault'?'High-voltage fault':'Hard fault',detail:s.fault.text};
 if(mode==='Cooling down'&&Number.isFinite(s.cooling_temp_c)&&!Number.isInteger(s.countdown))return {kind:'cooling',title:'Cooling down',detail:'Waiting to cool below 40 °C · now '+s.cooling_temp_c+' °C · reported by amplifier'};
 if(mode==='Warming up'||mode==='Cooling down') {
  const n=Number.isInteger(s.countdown)&&s.countdown>=0?s.countdown:null;
  const remaining=n===null?'Waiting for amplifier countdown':Math.floor(n/60)+':'+String(n%60).padStart(2,'0')+' remaining';
  return {kind:mode==='Warming up'?'warming':'cooling',title:mode,detail:remaining+' · reported by amplifier'};
 }
 if(s.rf_state_unknown)return {kind:'stale',title:'RF state unconfirmed',detail:mode+' · last RF reading is stale; controls paused'};
 if(s.transmitting===true)return {kind:'transmitting',title:'Transmitting',detail:mode==='Operate'?'Operate · RF active':'RF active · mode awaiting confirmation'};
 if(mode==='Operate')return {kind:'operate',title:'Operate',detail:'Amplifier enabled · no transmit indication'};
 if(mode==='Standby')return {kind:'standby',title:'Standby',detail:'Amplifier in standby'};
 if(mode==='Off')return {kind:'off',title:'Amplifier off',detail:'Network listener connected'};
 return {kind:'waiting',title:'Awaiting mode confirmation',detail:mode==='On'?'Powered on · waiting for operating mode':'Connected · operating mode not yet reported'};
}
/* "About amplifier" rows from the INFO reply, worded as in the vendor client. */
function formatOperatingTime(minutes){return Number.isFinite(minutes)&&minutes>=0?Math.floor(minutes/60)+'h '+(minutes%60)+'m':'—'}
function formatFirmware(version){const m=/^(\d+)\.(\d+)$/.exec(String(version||''));return m?String(parseInt(m[1],10))+'.'+m[2]:'—'}
function aboutAmplifier(info){
 const available=!!info&&typeof info.model==='string';
 return {available,rows:available?[['Type of PA',info.model],['Amplifier serial no.',info.serial||'—'],['PA firmware version',formatFirmware(info.firmware)],['Operating time',formatOperatingTime(info.operating_minutes)]]:[]};
}
if(typeof module!=='undefined')Object.assign(module.exports,{formatOperatingTime,formatFirmware,aboutAmplifier});

/* Non-fault amplifier alerts (WGx/FAx warnings, soft-start error) shown beside, not instead of, the operating state.
   Serious faults arrive separately as s.fault, so a warning shows here even while a fault holds the state line. */
function alertPresentation(s){
 const a=s.alert;
 if(!a||a.kind==='hard_fault'||a.kind==='hv_fault')return {visible:false,kind:'',text:''};
 return {visible:true,kind:a.kind,text:a.text};
}
if(typeof module!=='undefined')Object.assign(module.exports,{amplifierPresentation,alertPresentation});

/* Operating commands need a model whose controls were validated on hardware (profiles.py). Without
   a server-supplied profile, fall back to the OM-3501A name check; whenUnknown covers a missing model. */
function controlsVerified(s,whenUnknown){
 if(s.model_profile)return s.model_profile.controls_verified===true;
 const model=s.settings?.model;return model?model==='OM-3501A':whenUnknown;
}
if(typeof module!=='undefined')module.exports.controlsVerified=controlsVerified;

function amplifierControls(s,localPending=false){
 const mode=s.status||'Unknown',c=s.control||{};
 let reason='';
 if(s.readiness_test)reason='Restricted no-RF readiness test: commands are managed by the test; keep the radio idle.';
 else if(s.power_test)reason='Restricted power-cycle test: commands are managed by the test; Operate and tuning are blocked.';
 else if(s.mode_test)reason='Restricted Operate/Standby test: commands are managed by the test; power and tuning are blocked.';
 else if(s.read_only)reason='Read-only telemetry: operating and tuning commands are blocked.';
 else if(!controlsVerified(s,true))reason='Monitoring only: controls are unverified for this model.';
 else if(s.fault)reason='Amplifier fault active: commands are blocked. '+s.fault.text;
 else if(s.model_pending)reason='Waiting for the amplifier to report its model before enabling controls.';
 else if(s.connection!=='Connected'||s.age_seconds>freshSeconds(s))reason='Connect and wait for fresh amplifier data to use controls.';
 else if(c.uncertain)reason='Command result is uncertain. Reconnect to reassess; no retry was sent.';
 else if(localPending||c.pending)reason='Waiting for amplifier confirmation…';
 else if(['entered','waiting','tuning','unknown','aborted'].includes(s.autotune_phase))reason='Automatic tuning active; use its controls below.';
 else if(s.rf_state_unknown)reason='RF state is unconfirmed. Keep RF off and check the amplifier; controls remain paused.';
 else if(s.transmitting)reason='Stop transmission before changing amplifier state.';
 else if(mode==='Cooling down'||mode==='Warming up')reason='Wait for the amplifier countdown to finish.';
 else if(c.cooldown_remaining>0)reason='Waiting briefly before another command.';
 const disabled=!!reason;
 return {reason,
  toggle:{label:mode==='Operate'?'Go to Standby':mode==='Standby'?'Go to Operate':'Toggle Operate / Standby',disabled:disabled||mode==='Off'||!!(s.tune_test&&s.tune_test_counts?.O>=2),expectedMode:['Operate','Standby'].includes(mode)?mode:null},
  on:{label:'Power on',disabled:disabled||!!s.tune_test||['On','Operate','Standby'].includes(mode)},
  off:{label:'Power off',disabled:disabled||!!s.tune_test||mode==='Off'}
 };
}
if(typeof module!=='undefined')module.exports.amplifierControls=amplifierControls;

function amplifierConnection(s){
 if(s.simulated)return {endpoint:'Offline simulator',kind:'simulation',badge:'SIMULATION',label:'Offline simulation',detail:'Synthetic readings only; no amplifier connection',error:''};
 const endpoint=s.settings?String(s.settings.host)+':'+String(s.settings.port):'';
 let state=s.connection||'Disconnected';
 if(state==='Connected'&&s.age_seconds>freshSeconds(s))state='Stale';
 let result={endpoint,kind:'offline',badge:'OFFLINE',label:'Disconnected',detail:'No amplifier connection',error:''};
 if(state==='Connected')result={...result,kind:'live',badge:'LIVE',label:'Connected',detail:'Receiving amplifier data'};
 else if(state==='Disconnecting')result={...result,kind:'waiting',badge:'CLOSING',label:'Disconnecting',detail:'Closing amplifier communication session'};
 else if(state==='Connecting')result={...result,kind:'waiting',badge:'CONNECTING',label:'Connecting',detail:s.connect_note||'Opening amplifier connection'};
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

// The gradient occupies the whole track, whose full scale comes from the model profile (default 3500 W).
// Reveal it without rescaling its colors.
function forwardPowerClip(watts,fullScale=3500){const value=typeof watts==='number'&&Number.isFinite(watts)?Math.max(0,Math.min(fullScale,watts)):0;return 'inset(0 '+(100-value/fullScale*100).toFixed(3)+'% 0 0)'}
function forwardPowerScale(s){const w=s?.model_profile?.full_scale_w;return Number.isFinite(w)&&w>0?w:3500}
/* Positioned scale marks {position:%, label}. A profile list (watts, shown as kW) replaces the five even steps. */
function forwardPowerMarks(s){
 const full=forwardPowerScale(s),list=s?.model_profile?.forward_ticks_w;
 if(Array.isArray(list)&&list.length>1)return list.map(w=>({position:100*w/full,label:w===0?'0':(w/1000).toLocaleString('en-US',{minimumFractionDigits:1,maximumFractionDigits:1})}));
 return forwardPowerTicks(full).map((label,i)=>({position:i*20,label}));
}
function forwardPowerTicks(fullScale){return [0,1,2,3,4,5].map(i=>(fullScale*i/5).toLocaleString('en-US',{maximumFractionDigits:0})+(i===5?' W':''))}
if(typeof module!=='undefined'){module.exports.forwardPowerClip=forwardPowerClip;module.exports.forwardPowerScale=forwardPowerScale;module.exports.forwardPowerTicks=forwardPowerTicks;module.exports.forwardPowerMarks=forwardPowerMarks;}

// Both readings describe the same mismatch. Color only fresh, active RF data.
function mismatchColor(s){
 const neutral='#a5b2b6';
 if(s.connection!=='Connected'||s.age_seconds>freshSeconds(s)||s.transmitting!==true||
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
 const range=s.model_profile?.screen_ma_range;
 const screen=profile===OM3501A_PROFILE;
 if(screen&&Array.isArray(range)&&range.length===2&&range[0]<range[1])profile={...profile,min:range[0],max:range[1]};
 const value=s[profile.key],valid=s.connection==='Connected'&&!(s.age_seconds>freshSeconds(s))&&typeof value==='number'&&Number.isFinite(value);
 const position=valid?100*(Math.max(profile.min,Math.min(profile.max,value))-profile.min)/(profile.max-profile.min):50;
 const sign=v=>v>0?'+'+v:v<0?'\u2212'+(-v):'0',step=s.model_profile?.screen_ma_tick_step,span=profile.max-profile.min;
 const values=!screen||!(step>0)||span/step>40?[0,1,2,3,4].map(i=>Math.round((profile.min+span*i/4)*10)/10):Array.from({length:Math.floor(span/step)+1},(_,i)=>profile.min+i*step);
 const ticks=values.map(v=>({position:100*(v-profile.min)/span,label:sign(v)}));
 return {label:profile.label,unit:profile.unit,value:valid?value:null,position,min:profile.min,max:profile.max,ticks};
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
 const base=SECONDARY_PROFILES[key],v=s[key];
 const limit={reflected:s.model_profile?.reflected_max_w,input:s.model_profile?.input_max_w}[key];
 const p=Number.isFinite(limit)&&limit>0?{...base,max:limit}:base;
 const valid=s.connection==='Connected'&&!(s.age_seconds>freshSeconds(s))&&typeof v==='number'&&Number.isFinite(v);
 const value=valid?v:null,position=value===null?0:100*Math.max(0,Math.min(p.max,value))/p.max;
 const list={reflected:s.model_profile?.reflected_ticks_w,input:s.model_profile?.input_ticks_w}[key],custom=Array.isArray(list)&&list.length>1;
 const ticks=custom?list:[0,p.max/2,p.max];
 const tickMarks=ticks.map((v,i)=>({position:100*v/p.max,label:v.toLocaleString('en-US',{maximumFractionDigits:2})+(!custom&&i===ticks.length-1?' '+p.unit:'')}));
 return {...p,key,value,position,ticks,tickMarks,color:key==='reflected'?mismatchColor(s):value===null?'#a5b2b6':'#79d5b3'};
}
if(typeof module!=='undefined'){module.exports.secondaryMeter=secondaryMeter;module.exports.SECONDARY_PROFILES=SECONDARY_PROFILES;}

function autotunePresentation(s,pending=false){
 const phase=s.autotune_phase||'idle',active=['entered','waiting','tuning','unknown','aborted'].includes(phase),link=s.connection==='Connected'&&!(s.age_seconds>freshSeconds(s));
 let reason='';if(s.readiness_test)reason='No-RF readiness test: commands are managed by the test; do not transmit.';else if(s.power_test)reason='Restricted power-cycle test: tuning commands are blocked.';else if(s.mode_test)reason='Restricted Operate/Standby test: tuning commands are blocked.';else if(s.read_only)reason='Read-only telemetry: operating and tuning commands are blocked.';else if(!controlsVerified(s,false))reason='Auto-tune is verified only for OM-3501A.';else if(!link)reason='Fresh amplifier communication is required.';else if(pending||s.control?.pending)reason='Waiting for command confirmation.';else if(s.control?.uncertain)reason='Command result uncertain; check amplifier. No retry was sent.';else if(s.rf_state_unknown)reason='RF state is unconfirmed; keep RF off and check the amplifier.';else if(s.transmitting)reason='Stop RF before using tuning controls.';else if(s.control?.cooldown_remaining>0)reason='Please wait before another command.';
 let title={idle:'Automatic tuning',entered:'Preparing auto-tune',waiting:'WAITING FOR INPUT POWER',tuning:'AUTO-TUNE IN PROGRESS',succeeded:'SUCCESSFUL AUTOTUNE!',cancelled:'Auto-tune exited',aborted:'AUTO-TUNE ABORTED',defaults:'Auto-tune exited · defaults restored','stopped-exited':'Stopped tune exited · settings saved',unknown:'Unexpected auto-tune response'}[phase]||'Unexpected auto-tune response';
 let detail={idle:'Operator sets tuning power and supplies the steady carrier.',entered:'Waiting for amplifier readiness.',waiting:'Set the prescribed tuning drive level, then transmit a steady carrier from your radio.',tuning:'Operator controls RF. Stop RF manually if tuning is abnormal.',succeeded:s.autotune_saved?'Amplifier reported settings saved automatically. Stop tuning RF.':'Amplifier reported tuning complete. Stop tuning RF.',cancelled:'Returned from automatic tuning without applying RF.',aborted:s.autotune_abort_origin==='rf_lost'?'RF was released before completion. Exit auto-tune to restore default settings; this was not a successful tune.':s.autotune_abort_origin==='stop'?'Tuning was stopped. Release RF, then use Exit; the amplifier may save its current settings. This is not a successful tune.':'Stop RF manually and check the amplifier. The abort cause is unrecognized.',defaults:'Amplifier reported default settings saved. No successful tune was saved.','stopped-exited':'Amplifier reported user settings saved after Stop. Successful tuning was not confirmed.',unknown:(s.autotune_message||'Unrecognized response')+' · Stop RF and check the amplifier; no retry is sent.'}[phase];
 if(active&&!link){title='Auto-tune result unknown';detail='Communication interrupted. Stop RF manually and check the amplifier.';}
 else if(active&&s.autotune_age_seconds>15){title='Auto-tune status delayed';detail='No recent tuning status. Stop RF manually and check the amplifier; no retry is sent.';}
 if(s.readiness_test)detail='NO-RF TEST: do not transmit. Verify readiness, Exit, then return to Standby; no successful tune is expected.';
 if(s.rf_state_unknown)detail+=' RF state is unconfirmed; keep RF off and check the amplifier.';
 const stopBlocked=s.read_only||s.mode_test||s.power_test||s.readiness_test||!controlsVerified(s,false)||!link||pending||s.control?.pending||s.control?.uncertain||phase!=='tuning';
 const pct=v=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(1)+' %':null;
 const parts=[['Load',pct(s.load_pct)],['Tune',pct(s.tune_pct)]].filter(x=>x[1]).map(x=>x.join(' '));
 const positions=link&&phase!=='idle'&&!(active&&s.autotune_age_seconds>15)&&parts.length?'Capacitor positions · '+parts.join(' · '):'';
 return {positions,stopDisabled:!!stopBlocked||!!(s.tune_test&&s.tune_test_counts?.['8']),phase,title,detail,visible:phase!=='idle',startDisabled:!!reason||active||s.status!=='Operate'||!!(s.tune_test&&s.tune_test_counts?.L),exitDisabled:!!reason||!!(s.tune_test&&s.tune_test_counts?.['*'])||(phase!=='waiting'&&!(phase==='aborted'&&['rf_lost','stop'].includes(s.autotune_abort_origin))),reason};
}
if(typeof module!=='undefined')module.exports.autotunePresentation=autotunePresentation;

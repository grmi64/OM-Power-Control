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

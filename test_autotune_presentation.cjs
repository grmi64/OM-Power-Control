const assert=require('assert/strict'),{autotunePresentation,amplifierControls}=require('./presentation.js');
const state={connection:'Connected',age_seconds:0,status:'Operate',transmitting:false,control:{},settings:{model:'OM-3501A'}};
assert.equal(autotunePresentation(state).startDisabled,false);
for(const phase of ['entered','waiting','tuning','unknown']){const s={...state,autotune_phase:phase};assert(autotunePresentation(s).startDisabled);assert(amplifierControls(s).off.disabled);assert.equal(autotunePresentation(s).exitDisabled,phase!=='waiting');}
assert(autotunePresentation({...state,autotune_phase:'tuning',autotune_age_seconds:16}).title.includes('delayed'));
assert(autotunePresentation({...state,autotune_phase:'waiting',connection:'Disconnected'}).title.includes('unknown'));
assert(autotunePresentation({...state,autotune_phase:'unknown',autotune_message:'AUTO:FAULT'}).detail.includes('AUTO:FAULT'));
assert.equal(autotunePresentation({...state,autotune_phase:'succeeded',autotune_saved:true}).title,'SUCCESSFUL AUTOTUNE!');
assert(autotunePresentation({...state,transmitting:true}).startDisabled);assert(autotunePresentation({...state,settings:{model:'OM-4001A'}}).startDisabled);
console.log('Auto-tune presentation guards, saved success, unknown replies, delayed status and connection loss pass.');
assert.equal(autotunePresentation({...state,transmitting:true,autotune_phase:'tuning',control:{cooldown_remaining:1}}).stopDisabled,false);
assert(autotunePresentation({...state,autotune_phase:'waiting'}).stopDisabled);
assert.equal(autotunePresentation({...state,autotune_phase:'aborted'}).title,'AUTO-TUNE ABORTED');
assert.equal(autotunePresentation({...state,autotune_phase:'aborted',autotune_abort_origin:'rf_lost'}).exitDisabled,false);
assert.equal(autotunePresentation({...state,autotune_phase:'aborted',autotune_abort_origin:'stop'}).exitDisabled,false);
assert(autotunePresentation({...state,autotune_phase:'defaults'}).title.includes('defaults restored'));

assert(autotunePresentation({...state,autotune_phase:'stopped-exited'}).title.includes('Stopped tune exited'));assert(!autotunePresentation({...state,autotune_phase:'stopped-exited'}).title.includes('SUCCESSFUL'));

const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/live.html','utf8');
const script=html.split('<script>')[1].split('</script>')[0].replace('__PRESENTATION__',fs.readFileSync(__dirname+'/presentation.js','utf8'));
const nodes={},node=id=>nodes[id]??={textContent:'',value:'',disabled:false,hidden:false,checked:false,dataset:{},style:{},classList:{toggle(){},remove(){}},setAttribute(){},removeAttribute(){}};
const posts=[],native=[],listeners={};
let state={simulated:true,connection:'Connected',status:'Standby',transmitting:false,age_seconds:0,control:{},settings:{host:'simulation',model:'OM-3501A',port:10001,auto_connect:false}};
const ctx=vm.createContext({document:{getElementById:node,body:{classList:{toggle(){}}}},window:{omPreferences:{compact:true,alwaysOnTop:true},addEventListener:(name,fn)=>listeners[name]=fn,pywebview:{api:{display_window:async value=>native.push(value)}}},localStorage:{getItem(){},setItem(){}},crypto:{randomUUID:()=> 'offline-ui-123'},setTimeout(){},confirm:()=>true,fetch:async(path,o)=>{if(o?.method==='POST')posts.push({path,body:JSON.parse(o.body||'{}')});return {ok:true,json:async()=>path==='/state'?state:{}};}});
vm.runInContext(script,ctx);
(async()=>{
 await new Promise(r=>setImmediate(r));
 assert.equal(nodes.simulationPanel.hidden,false);assert.equal(nodes.shareDXC.disabled,true);
 assert.equal(nodes.view.textContent,'Full view');assert.equal(nodes.onTop.checked,true);
 assert.equal(native.at(-1).compact,true);listeners.pywebviewready();
 nodes.view.onclick();assert.equal(native.at(-1).compact,false);
 nodes.onTop.checked=false;nodes.onTop.onchange();assert.equal(native.at(-1).alwaysOnTop,false);
 node('simScenario').value='unexpected';await nodes.simRFOn.onclick();
 assert.equal(posts.at(-1).path,'/simulation');assert.deepEqual(posts.at(-1).body,{rf:true,scenario:'unexpected'});
 await nodes.simRFOff.onclick();assert.equal(posts.at(-1).body.rf,false);
 state={...state,transmitting:true};await vm.runInContext('refresh()',ctx);
 assert.equal(nodes.simRFOn.disabled,true);assert.match(nodes.simRFState.textContent,/operator must stop RF/);
 state={...state,simulated:false};await vm.runInContext('refresh()',ctx);assert.equal(nodes.simulationPanel.hidden,true);
 state={...state,read_only:true,status:'Operate',autotune_phase:'tuning'};await vm.runInContext('refresh()',ctx);
 assert.equal(nodes.readOnlyPanel.hidden,false);assert.equal(nodes.shareDXC.disabled,true);
 const beforeControls=posts.length;
 for(const id of ['toggle','on','off','autotuneStart','autotuneExit','autotuneStop']){assert.equal(nodes[id].disabled,true,id);await nodes[id].onclick();}
 assert.equal(posts.length,beforeControls,'Read-only UI must never submit operating or tuning commands');
 state={...state,read_only:false,mode_test:true,mode_test_sent:0};await vm.runInContext('refresh()',ctx);
 assert.match(nodes.readOnlyPanel.textContent,/Power and tuning are blocked/);
 for(const id of ['toggle','on','off','autotuneStart','autotuneExit','autotuneStop']){assert.equal(nodes[id].disabled,true,id);await nodes[id].onclick();}
 assert.equal(posts.length,beforeControls,'Scripted mode-test UI must not submit extra commands');
 state={...state,mode_test:false,power_test:true,power_test_sent:0};await vm.runInContext('refresh()',ctx);
 assert.match(nodes.readOnlyPanel.textContent,/Operate and tuning are blocked/);
 for(const id of ['toggle','on','off','autotuneStart','autotuneExit','autotuneStop']){assert.equal(nodes[id].disabled,true,id);await nodes[id].onclick();}
 assert.equal(posts.length,beforeControls,'Scripted power test UI must not submit extra commands');
 state={...state,power_test:false,readiness_test:true,readiness_test_sent:3,status:'Operate',autotune_phase:'waiting',transmitting:false};await vm.runInContext('refresh()',ctx);
 assert.match(nodes.readOnlyPanel.textContent,/Keep the radio idle/);assert.match(nodes.autotuneDetail.textContent,/do not transmit/);
 for(const id of ['toggle','on','off','autotuneStart','autotuneExit','autotuneStop']){assert.equal(nodes[id].disabled,true,id);await nodes[id].onclick();}
 assert.equal(posts.length,beforeControls,'No-RF test UI must not submit extra commands');
 console.log('Windows UI: preferences, native bridge, simulated RF controls and visible simulation label pass.');
})().catch(e=>{console.error(e);process.exitCode=1});

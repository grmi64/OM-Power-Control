const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/live.html','utf8');
const script=html.split('<script>')[1].split('</script>')[0].replace('__PRESENTATION__',fs.readFileSync(__dirname+'/presentation.js','utf8'));
const nodes={};const node=id=>nodes[id]??=( {id,textContent:'',value:'',disabled:false,hidden:false,checked:false,title:'',style:{},setAttribute(){},removeAttribute(){},dataset:{},classList:{toggle(){},remove(){}}} );
let state={connection:'Connected',status:'Standby',age_seconds:0,control:{},settings:{host:'192.0.2.1',port:10001,callsign:'W1AW',auto_connect:false}};
const posts=[],confirmations=[];
const ctx=vm.createContext({document:{getElementById:node,body:{classList:{toggle(){}}}},window:{},localStorage:{getItem(){return null},setItem(){}},crypto:{randomUUID:()=> 'test-request-123'},setTimeout(){},confirm:text=>{confirmations.push(text);return false},fetch:async(path,options)=>{if(options?.method==='POST')posts.push({path,body:JSON.parse(options.body||'{}')});return {ok:true,json:async()=>path==='/state'?state:{}}}});
vm.runInContext(script,ctx);
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 await flush();
 state={...state,frequency_khz:7074,temperature_c:23};await vm.runInContext('refresh()',ctx);assert.equal(nodes.frequency.textContent,'7.074 MHz');assert.equal(nodes.temperature.textContent,'23 °C');
 state={...state,frequency_khz:null,temperature_c:null};await vm.runInContext('refresh()',ctx);assert.equal(nodes.frequency.textContent,'— MHz');assert.equal(nodes.temperature.textContent,'— °C');
 assert.equal(nodes.swr.style.color,'#a5b2b6');assert.equal(nodes.reflected.style.color,'#a5b2b6');
 state={...state,transmitting:true,forward:1000,reflected:120,swr:2.1};await vm.runInContext('refresh()',ctx);assert.equal(nodes.swr.style.color,'rgb(229, 103, 88)');assert.equal(nodes.reflected.style.color,nodes.swr.style.color);
 state={...state,transmitting:false,forward:0,reflected:0,swr:null};await vm.runInContext('refresh()',ctx);assert.equal(nodes.swr.style.color,'#a5b2b6');
 assert.equal(nodes.stationCall.textContent,'W1AW');assert.equal(nodes.stationCall.hidden,false);
 await nodes.toggle.onclick();assert.equal(confirmations.length,0);assert.equal(posts.length,1);assert.equal(posts[0].path,'/control/toggle');assert.equal(posts[0].body.expected_mode,'Standby');
 await nodes.off.onclick();assert.equal(confirmations.length,1);assert.equal(posts.length,1);
 state={...state,status:'Off'};await vm.runInContext('refresh()',ctx);await nodes.on.onclick();assert.equal(confirmations.length,2);assert.equal(posts.length,1);
 state={...state,transmitting:true,status:'Operate'};await vm.runInContext('refresh()',ctx);await nodes.toggle.onclick();assert.equal(posts.length,1);
 state={...state,settings:{...state.settings,callsign:''}};await vm.runInContext('loadedSettings=false;refresh()',ctx);assert.equal(nodes.stationCall.hidden,true);
 state={...state,connection:'Connected',age_seconds:0,input:21,plate_a:.86,gain_db:18.3};
 for(const [key,label,value,max] of [['input','INPUT POWER · W','21',100],['plate_a','PLATE CURRENT · A','0.86',3],['gain_db','CALC GAIN · dB','18.3',30],['reflected','REFLECTED · W','0',500]]){
  nodes.secondaryChoice.value=key;await nodes.secondaryChoice.onchange();await vm.runInContext('refresh()',ctx);
  assert.equal(nodes.secondaryLabel.textContent,label);assert.equal(nodes.reflected.textContent,value);assert.equal(nodes['metricOption_'+key].disabled,true);
  assert.equal(posts.at(-1).path,'/display-settings');assert.deepEqual(posts.at(-1).body,{secondary_measurement:key});
 }
 let finishSave;const oldFetch=ctx.fetch;ctx.fetch=()=>new Promise(resolve=>finishSave=resolve);
 const saving=nodes.save.onclick();assert.equal(nodes.save.disabled,true);assert.equal(nodes.save.textContent,'Saving…');assert.equal(nodes.settingsSaveStatus.textContent,'Saving settings…');
 finishSave({ok:true,json:async()=>({})});await saving;assert.equal(nodes.save.disabled,false);assert.equal(nodes.settingsSaveStatus.textContent,'Settings saved.');
 ctx.fetch=async()=>({ok:false,json:async()=>({error:'Disk full'})});await nodes.save.onclick();assert.equal(nodes.settingsSaveStatus.dataset.error,'true');assert.match(nodes.settingsSaveStatus.textContent,/not saved: Disk full/);ctx.fetch=oldFetch;
 // Compact key readings and per-model tube labels (OM-4001A shows grid f/b separately).
 state={...state,connection:'Connected',age_seconds:0,plate_a:.85,plate_v:2900,screen_v:300,grid_v:-75,grid_a_v:75,grid_b_v:150,heater_a_v:27.8,heater_b_v:27.6,mains_v:239,model_profile:{tube_labels:['f','b'],grid_separate:true,full_scale_w:5000,screen_ma_range:[-80,80],screen_ma_tick_step:20,forward_ticks_w:[0,2500,5000]}};
 await vm.runInContext('refresh()',ctx);
 assert.equal(nodes.key_plate_a.textContent,'0.85 A');assert.equal(nodes.key_plate_v.textContent,'2,900 V');assert.equal(nodes.key_screen_v.textContent,'300 V');
 assert.equal(nodes.key_grid_a_v.textContent,'75 V');assert.equal(nodes.key_heater_a_v.textContent,'27.8 V');assert.equal(nodes.key_heater_b_v.textContent,'27.6 V');assert.equal(nodes.key_mains_v.textContent,'239 V');assert.equal(nodes.keylabel_heater_a_v.textContent,'Uheat f');assert.equal(nodes.key_grid_b_v.textContent,'150 V');
 assert.equal(nodes.keycell_grid_v.hidden,true);assert.equal(nodes.keycell_grid_a_v.hidden,false);assert.equal(nodes.keycell_grid_b_v.hidden,false);
 assert.equal(nodes.keylabel_grid_a_v.textContent,'Ugrid f');assert.equal(nodes.label_heater_b_v.textContent,'Heater b · Uheat b');assert.equal(nodes.measurement_grid_b_v.textContent,'150 V');
 assert.match(nodes.powerTicks.innerHTML,/>2\.5</);assert.match(nodes.auxTicks.innerHTML,/\+80 mA/);
 state={...state,model_profile:undefined};await vm.runInContext('refresh()',ctx);
 assert.equal(nodes.keycell_grid_v.hidden,false);assert.equal(nodes.keycell_grid_a_v.hidden,true);assert.equal(nodes.keylabel_grid_a_v.textContent,'Ugrid A');assert.equal(nodes.keylabel_heater_b_v.textContent,'Uheat B');assert.match(nodes.powerTicks.innerHTML,/3,500 W/);
 // Simulator extras appear only when the simulator supports them.
 const before=posts.length;
 state={...state,simulated:true,sim_features:['power','alert']};await vm.runInContext('refresh()',ctx);assert.equal(nodes.simExtras.hidden,false);
 node('simAlert').value='HF';await nodes.simAlertSend.onclick();assert.deepEqual(posts.at(-1).body,{alert:'HF'});assert.equal(nodes.simExtraState.textContent,'Sent: HF');assert.equal(posts.at(-1).path,'/simulation');
 await nodes.simPowerOn.onclick();assert.deepEqual(posts.at(-1).body,{power:true});assert.equal(nodes.simExtraState.textContent,'Sent: PA on');await nodes.simPowerOff.onclick();assert.deepEqual(posts.at(-1).body,{power:false});assert.equal(posts.length,before+3);
 state={...state,sim_features:[]};await vm.runInContext('refresh()',ctx);assert.equal(nodes.simExtras.hidden,true);
 state={...state,simulated:false,sim_features:undefined};await vm.runInContext('refresh()',ctx);assert.equal(nodes.simExtras.hidden,true);
 // Simulated model picker: disconnect, wait for it, save the model, reconnect.
 {
  const seen=posts.length;state={...state,simulated:true,connection:'Disconnected',settings:{...state.settings,model:'OM-3501A'}};
  node('simModel').value='OM-4001A';await nodes.simModel.onchange();
  assert.deepEqual(posts.slice(seen).map(p=>p.path),['/disconnect','/settings','/connect']);assert.deepEqual(posts[seen+1].body,{model:'OM-4001A'});assert.equal(nodes.simModelState.textContent,'Model: OM-4001A');
  ctx.fetch=async(path,options)=>{if(options?.method==='POST')return {ok:false,json:async()=>({error:'Disconnect before changing amplifier address, port or model'})};return {ok:true,json:async()=>state}};
  await nodes.simModel.onchange();assert.match(nodes.simModelState.textContent,/Disconnect before changing/);
 }
 // About amplifier panel and model notice.
 state={...state,simulated:false,info:{model:'OM4001A',serial:'2302',firmware:'03.42',operating_minutes:55756},model_notice:''};await vm.runInContext('refresh()',ctx);
 for(const text of ['Type of PA','OM4001A','Amplifier serial no.','2302','PA firmware version','3.42','Operating time','929h 16m'])assert.ok(nodes.aboutRows.innerHTML.includes('>'+text+'<'),text);
 assert.equal(nodes.modelNotice.hidden,true);
 state={...state,info:{model:'<b>X</b>',firmware:'03.42',operating_minutes:1},model_notice:'Amplifier reports X.'};await vm.runInContext('refresh()',ctx);
 assert.ok(!nodes.aboutRows.innerHTML.includes('<b>'));assert.equal(nodes.modelNotice.hidden,false);assert.equal(nodes.modelNotice.textContent,'Amplifier reports X.');
 state={...state,info:undefined,model_notice:''};await vm.runInContext('refresh()',ctx);assert.ok(nodes.aboutRows.innerHTML.includes('Available after connecting.'));assert.equal(nodes.modelNotice.hidden,true);
 console.log('Actual UI handlers: toggle skips prompt; power confirmations retained; RF guard and callsign badge pass');
})().catch(e=>{console.error(e);process.exitCode=1});

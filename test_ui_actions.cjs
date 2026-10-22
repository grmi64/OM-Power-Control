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
 console.log('Actual UI handlers: toggle skips prompt; power confirmations retained; RF guard and callsign badge pass');
})().catch(e=>{console.error(e);process.exitCode=1});

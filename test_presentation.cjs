const assert=require('node:assert/strict');const {amplifierPresentation:p}=require('./presentation.js');
const live={connection:'Connected'};
for(const [status,kind] of [['Operate','operate'],['Standby','standby'],['Off','off'],['On','waiting'],['Unknown','waiting']])assert.equal(p({...live,status}).kind,kind);
assert.equal(p({...live,status:'Operate',transmitting:true}).title,'Transmitting');
assert.equal(p({connection:'Disconnected',status:'Operate',transmitting:true}).title,'Disconnected');
assert.equal(p({connection:'Stale',status:'Operate',transmitting:true}).kind,'stale');
assert.equal(p({connection:'Connecting',status:'Operate'}).title,'Connecting');
assert.equal(p({connection:'Waiting for amplifier data'}).kind,'waiting');
assert.equal(p({...live,status:'Warming up',countdown:130}).detail,'2:10 remaining · reported by amplifier');
assert.equal(p({...live,status:'Cooling down',countdown:0}).title,'Cooling down');
assert.match(p({...live,status:'Cooling down',countdown:-1}).detail,/Waiting/);
const s=Object.freeze({...live,status:'Standby'});p(s);assert.equal(s.status,'Standby');
console.log('State presentation checks passed');
const {amplifierControls:c}=require('./presentation.js');
assert.equal(c({...live,status:'Operate'}).toggle.label,'Go to Standby');
assert.equal(c({...live,status:'Standby'}).toggle.label,'Go to Operate');
assert.equal(c({...live,status:'Unknown'}).toggle.label,'Toggle Operate / Standby');
assert.equal(c({...live,status:'Standby'}).toggle.expectedMode,'Standby');
assert.equal(c({...live,status:'Unknown'}).toggle.expectedMode,null);
for(const status of ['Operate','Standby','On'])assert.equal(c({...live,status}).on.disabled,true);
assert.equal(c({...live,status:'Off'}).off.disabled,true);
assert.equal(c({...live,status:'Off'}).on.disabled,false);
assert.equal(c({...live,status:'Off'}).toggle.disabled,true);
for(const extra of [{transmitting:true},{connection:'Stale'},{age_seconds:4},{control:{pending:true}},{control:{uncertain:true}},{control:{cooldown_remaining:1}},{status:'Warming up'},{status:'Cooling down'}]){
 const v=c({...live,status:'Standby',...extra});for(const key of ['toggle','on','off'])assert.equal(v[key].disabled,true);assert.ok(v.reason);
}
console.log('Control labels and availability checks passed');
const {amplifierConnection:link}=require('./presentation.js');
const prefs={host:'192.0.2.1',port:10001};
for(const [connection,kind,badge] of [['Connected','live','LIVE'],['Connecting','waiting','CONNECTING'],['Waiting for amplifier data','waiting','WAITING'],['Stale','stale','DELAYED'],['Disconnected','offline','OFFLINE']]){
 const v=link({connection,settings:prefs});assert.equal(v.kind,kind);assert.equal(v.badge,badge);assert.equal(v.endpoint,'192.0.2.1:10001');
}
assert.equal(link({connection:'Connected',age_seconds:4}).kind,'stale');
assert.match(link({connection:'Disconnected',error:'No connection acknowledgement'}).error,/acknowledge/);
assert.match(link({connection:'Disconnected',error:'[Errno 65] No route to host'}).error,/Cannot reach/);
assert.match(link({connection:'Disconnected',error:'No amplifier data for 10 seconds'}).error,/10 seconds/);
assert.equal(link({connection:'Connected'}).error,'');
console.log('Shared connection feedback checks passed');
assert.equal(link({connection:'Disconnecting'}).badge,'CLOSING');
assert.equal(p({connection:'Disconnecting'}).title,'Disconnecting');
assert.equal(c({connection:'Disconnecting'}).toggle.disabled,true);
const {forwardPowerClip:clip}=require('./presentation.js');
for(const value of [null,undefined,NaN,Infinity,-100])assert.equal(clip(value),'inset(0 100.000% 0 0)');
assert.equal(clip(0),'inset(0 100.000% 0 0)');assert.equal(clip(1500),'inset(0 57.143% 0 0)');assert.equal(clip(2500),'inset(0 28.571% 0 0)');assert.equal(clip(3500),'inset(0 0.000% 0 0)');assert.equal(clip(5000),clip(3500));
console.log('Fixed wattage gradient clipping checks passed');

const {mismatchColor:mc}=require('./presentation.js');
const rf={connection:'Connected',age_seconds:0,transmitting:true,forward:1000,reflected:40,swr:1.5};
assert.equal(mc({...rf,swr:1}),'rgb(121, 213, 179)');
assert.equal(mc(rf),'rgb(241, 187, 103)');
assert.equal(mc({...rf,swr:1.75}),'rgb(235, 145, 96)');
assert.equal(mc({...rf,swr:2}),'rgb(229, 103, 88)');
assert.equal(mc({...rf,swr:3}),mc({...rf,swr:2}));
for(const extra of [{connection:'Stale'},{age_seconds:4},{transmitting:false},{forward:0},{swr:null},{reflected:null},{swr:NaN}])assert.equal(mc({...rf,...extra}),'#a5b2b6');
console.log('Mismatch gradient and idle/unavailable checks passed');

for(const key of ['toggle','on','off'])assert.equal(c({...live,status:'Standby',settings:{model:'OM-4001A'}})[key].disabled,true);

const {auxiliaryMeter:aux}=require('./presentation.js');
for(const [value,position] of [[-80,0],[-60,0],[-30,25],[0,50],[30,75],[60,100],[80,100]])assert.equal(aux({connection:'Connected',screen_ma:value}).position,position);
assert.equal(aux({connection:'Stale',screen_ma:2}).value,null);assert.equal(aux({connection:'Connected',screen_ma:null}).value,null);
assert.equal(aux({connection:'Connected',plate_a:.5},{key:'plate_a',label:'Plate current',unit:'A',min:0,max:1}).position,50);
console.log('Configurable auxiliary meter checks passed');

const {secondaryMeter}=require('./presentation.js');
for(const [key,value,max] of [['reflected',250,500],['input',50,100],['plate_a',1.5,3],['gain_db',15,30]]){
 const m=secondaryMeter({connection:'Connected',[key]:value},key);assert.equal(m.position,50);assert.equal(m.value,value);assert.equal(m.max,max);assert.deepEqual(m.ticks,[0,max/2,max]);
 assert.equal(secondaryMeter({connection:'Stale',[key]:value},key).value,null);
 assert.equal(secondaryMeter({connection:'Connected',[key]:max*2},key).position,100);
 assert.equal(secondaryMeter({connection:'Connected',[key]:null},key).value,null);
}
console.log('Selectable secondary-meter ranges and unavailable states pass');

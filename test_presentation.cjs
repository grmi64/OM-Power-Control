const assert=require('node:assert/strict');const {amplifierPresentation:p}=require('./presentation.js');
const live={connection:'Connected'};
for(const [status,kind] of [['Operate','operate'],['Standby','standby'],['Off','off'],['On','waiting'],['Unknown','waiting']])assert.equal(p({...live,status}).kind,kind);
assert.equal(p({...live,status:'Operate',transmitting:true}).title,'Transmitting');
assert.equal(p({...live,status:'Operate',transmitting:null,rf_state_unknown:true}).title,'RF state unconfirmed');
assert.match(p({...live,status:'Standby',transmitting:null,rf_state_unknown:true}).detail,/Standby/);
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
for(const extra of [{transmitting:true},{transmitting:null,rf_state_unknown:true},{connection:'Stale'},{age_seconds:4},{control:{pending:true}},{control:{uncertain:true}},{control:{cooldown_remaining:1}},{status:'Warming up'},{status:'Cooling down'}]){
 const v=c({...live,status:'Standby',...extra});for(const key of ['toggle','on','off'])assert.equal(v[key].disabled,true);assert.ok(v.reason);
}
console.log('Control labels and availability checks passed');
const {amplifierConnection:link}=require('./presentation.js');
const prefs={host:'192.0.2.1',port:10001};
for(const [connection,kind,badge] of [['Connected','live','LIVE'],['Connecting','waiting','CONNECTING'],['Waiting for amplifier data','waiting','WAITING'],['Stale','stale','DELAYED'],['Disconnected','offline','OFFLINE']]){
 const v=link({connection,settings:prefs});assert.equal(v.kind,kind);assert.equal(v.badge,badge);assert.equal(v.endpoint,'192.0.2.1:10001');
}
assert.equal(link({connection:'Connected',age_seconds:4}).kind,'stale');
for(const connection of ['Connected','Stale','Disconnected']){
 const v=link({simulated:true,connection,settings:prefs});
 assert.equal(v.badge,'SIMULATION');assert.equal(v.kind,'simulation');
 assert.match(v.detail,/no amplifier connection/);assert.equal(v.endpoint,'Offline simulator');
}
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
{
 const {alertPresentation:a}=require('./presentation.js');
 const hard={kind:'hard_fault',code:null,title:'Hard fault',text:'Hard fault: plate-current limit exceeded.'};
 const warning={kind:'warning',code:11,text:'Warning: SWR is too high'};
 assert.equal(p({...live,status:'Operate',fault:hard}).kind,'fault');
 assert.equal(p({...live,status:'Operate',fault:{kind:'hv_fault',text:'HV'}}).title,'High-voltage fault');
 assert.equal(p({connection:'Disconnected',fault:hard}).title,'Disconnected');
 assert.equal(p({...live,status:'Operate',alert:{kind:'warning',code:1,text:'w'}}).kind,'operate');
 // A warning received after a fault (HF;WG11;) keeps the fault state and the command block, and shows the warning too.
 assert.equal(p({...live,status:'Operate',fault:hard,alert:warning}).kind,'fault');
 assert.equal(c({...live,status:'Operate',age_seconds:0,fault:hard,alert:warning}).toggle.disabled,true);
 assert.deepEqual(a({fault:hard,alert:warning}),{visible:true,kind:'warning',text:warning.text});
 assert.match(p({...live,status:'Cooling down',cooling_temp_c:52}).detail,/52 °C/);
 assert.match(p({...live,status:'Cooling down',cooling_temp_c:52,countdown:30}).detail,/0:30 remaining/);
 assert.equal(c({...live,status:'Operate',fault:hard}).toggle.disabled,true);
 assert.match(c({...live,status:'Operate',fault:hard}).reason,/fault active/i);
 assert.equal(c({...live,status:'Operate',age_seconds:0,alert:{kind:'warning',code:1,text:'w'}}).toggle.disabled,false);
 // Controls stay paused until the amplifier reports its model (delayed INFO).
 assert.equal(c({...live,status:'Standby',age_seconds:0,model_pending:true}).toggle.disabled,true);
 assert.match(c({...live,status:'Standby',age_seconds:0,model_pending:true}).reason,/report its model/);
 assert.equal(a({alert:hard}).visible,false);
 assert.deepEqual(a({alert:{kind:'limit',text:'Second limit exceeded: SWR is too high'}}),{visible:true,kind:'limit',text:'Second limit exceeded: SWR is too high'});
 assert.equal(a({}).visible,false);
 console.log('Alert presentation checks passed');
{
 const {autotunePresentation:t}=require('./presentation.js');
 const base={...live,age_seconds:0,settings:{model:'OM-3501A'},autotune_phase:'tuning',autotune_age_seconds:1,load_pct:69.7667,tune_pct:19.9333};
 assert.equal(t(base).positions,'Capacitor positions · Load 69.8 % · Tune 19.9 %');
 assert.equal(t({...base,tune_pct:undefined}).positions,'Capacitor positions · Load 69.8 %');
 assert.equal(t({...base,load_pct:undefined,tune_pct:undefined}).positions,'');
 assert.equal(t({...base,autotune_phase:'idle'}).positions,'');
 assert.equal(t({...base,autotune_age_seconds:20}).positions,'');
 assert.equal(t({...base,connection:'Disconnected'}).positions,'');
 console.log('Capacitor position presentation checks passed');
}
{
 const {forwardPowerClip:clip2,forwardPowerScale:scale,forwardPowerTicks:ticks,controlsVerified:cv,amplifierControls:ctl,autotunePresentation:tune}=require('./presentation.js');
 assert.equal(clip2(2000,4000),'inset(0 50.000% 0 0)');assert.equal(clip2(9999,4000),'inset(0 0.000% 0 0)');assert.equal(clip2(1500),'inset(0 57.143% 0 0)');
 assert.equal(scale({model_profile:{full_scale_w:4000}}),4000);assert.equal(scale({}),3500);assert.equal(scale({model_profile:{full_scale_w:0}}),3500);
 assert.deepEqual(ticks(3500),['0','700','1,400','2,100','2,800','3,500 W']);assert.deepEqual(ticks(4000),['0','800','1,600','2,400','3,200','4,000 W']);
 const m4={model_profile:{controls_verified:false,full_scale_w:4000},settings:{model:'OM-4001A'}},m3={model_profile:{controls_verified:true,full_scale_w:3500},settings:{model:'OM-3501A'}};
 assert.equal(cv(m4,true),false);assert.equal(cv(m3,false),true);assert.equal(cv({settings:{model:'OM-3501A'}},false),true);assert.equal(cv({settings:{model:'X'}},true),false);assert.equal(cv({},true),true);assert.equal(cv({},false),false);
 const up={...live,age_seconds:0,status:'Standby'};
 assert.equal(ctl({...up,...m4}).toggle.disabled,true);assert.match(ctl({...up,...m4}).reason,/Monitoring only/);assert.equal(ctl({...up,...m3}).toggle.disabled,false);
 assert.equal(tune({...up,...m4,status:'Operate'}).startDisabled,true);assert.equal(tune({...up,...m3,status:'Operate'}).startDisabled,false);
 console.log('Model profile presentation checks passed');
}
{
 const {auxiliaryMeter:aux2,secondaryMeter:sec}=require('./presentation.js');
 const mp={model_profile:{reflected_max_w:250,input_max_w:100,screen_ma_range:[-80,80]}},up={connection:'Connected',age_seconds:0};
 assert.equal(aux2({...up,...mp,screen_ma:0}).position,50);assert.equal(aux2({...up,...mp,screen_ma:40}).position,75);assert.equal(aux2({...up,...mp,screen_ma:-200}).position,0);
 assert.deepEqual(aux2({...up,...mp,screen_ma:0}).ticks.map(t=>t.label),['\u221280','\u221240','0','+40','+80']);
 assert.deepEqual(aux2({...up,screen_ma:0}).ticks.map(t=>t.label),['\u221260','\u221230','0','+30','+60']);
 assert.deepEqual(aux2({...up,model_profile:{screen_ma_range:[5,1]},screen_ma:0}).ticks.map(t=>t.label),['\u221260','\u221230','0','+30','+60']);
 assert.equal(sec({...up,...mp,reflected:125},'reflected').position,50);assert.equal(sec({...up,...mp,reflected:125},'reflected').ticks[2],250);
 assert.equal(sec({...up,reflected:250},'reflected').position,50);
 assert.equal(sec({...up,...mp,input:50},'input').position,50);assert.equal(sec({...up,...mp,plate_a:1.5},'plate_a').position,50);
 console.log('Per-model meter range checks passed');
}
{
 const {forwardPowerMarks:marks,auxiliaryMeter:aux3,secondaryMeter:sec3}=require('./presentation.js');
 const v4={model_profile:{full_scale_w:5000,reflected_max_w:250,input_max_w:100,screen_ma_range:[-80,80],screen_ma_tick_step:20,forward_ticks_w:[0,400,800,1200,1600,2000,2400,2800,3200,3600,4000,4400,4800],reflected_ticks_w:[0,50,100,150,200,250],input_ticks_w:[0,10,20,30,40,50,60,70,80,90]}},up={connection:'Connected',age_seconds:0};
 const fm=marks(v4);assert.equal(fm.length,13);assert.deepEqual(fm.map(m=>m.label).slice(0,6),['0','0.4','0.8','1.2','1.6','2.0']);assert.equal(fm[10].label,'4.0');assert.equal(fm[12].label,'4.8');assert.equal(fm[12].position,96);assert.equal(fm[0].position,0);
 assert.deepEqual(marks({}).map(m=>m.label),['0','700','1,400','2,100','2,800','3,500 W']);assert.deepEqual(marks({}).map(m=>m.position),[0,20,40,60,80,100]);
 const at=aux3({...up,...v4,screen_ma:0}).ticks;assert.equal(at.length,9);assert.deepEqual(at.map(t=>t.label),['\u221280','\u221260','\u221240','\u221220','0','+20','+40','+60','+80']);assert.equal(at[4].position,50);
 const rm=sec3({...up,...v4,reflected:50},'reflected');assert.deepEqual(rm.tickMarks.map(t=>t.label),['0','50','100','150','200','250']);assert.equal(rm.tickMarks[1].position,20);assert.equal(rm.position,20);
 const im=sec3({...up,...v4,input:90},'input');assert.equal(im.tickMarks.length,10);assert.equal(im.tickMarks[9].position,90);assert.equal(im.position,90);
 const dm=sec3({...up,reflected:1},'reflected');assert.deepEqual(dm.tickMarks.map(t=>t.label),['0','250','500 W']);assert.deepEqual(dm.tickMarks.map(t=>t.position),[0,50,100]);
 console.log('Vendor-style scale mark checks passed');
}
{
 const {amplifierConnection:conn}=require('./presentation.js');
 const note='Waiting for network access to the amplifier. If macOS asks, choose Allow.';
 assert.equal(p({connection:'Connecting',connect_note:note}).detail,note);assert.equal(p({connection:'Connecting'}).detail,'Opening amplifier connection');
 assert.equal(conn({connection:'Connecting',connect_note:note,settings:{host:'h',port:1}}).detail,note);assert.equal(conn({connection:'Connecting',settings:{host:'h',port:1}}).detail,'Opening amplifier connection');
 console.log('Connect wait note presentation checks passed');
}
{
 const {freshSeconds:fresh,amplifierConnection:conn2,amplifierPresentation:pres}=require('./presentation.js');
 assert.equal(fresh({}),3);assert.equal(fresh({model_profile:{fresh_seconds:8}}),8);assert.equal(fresh({model_profile:{fresh_seconds:0}}),3);
 const base={connection:'Connected',status:'Off',settings:{host:'h',port:1},age_seconds:5};
 assert.equal(conn2(base).kind,'stale');assert.equal(conn2({...base,model_profile:{fresh_seconds:8}}).kind,'live');assert.equal(conn2({...base,model_profile:{fresh_seconds:8},age_seconds:9}).kind,'stale');
 assert.equal(pres({...base,model_profile:{fresh_seconds:8}}).kind,'off');
 console.log('Per-model freshness presentation checks passed');
}
{
 const {aboutAmplifier:about,formatOperatingTime:hm,formatFirmware:fw}=require('./presentation.js');
 assert.equal(hm(55756),'929h 16m');assert.equal(hm(0),'0h 0m');assert.equal(hm(59),'0h 59m');assert.equal(hm(60),'1h 0m');assert.equal(hm(355),'5h 55m');
 for(const bad of [undefined,null,NaN,-1,'x'])assert.equal(hm(bad),'—');
 assert.equal(fw('03.42'),'3.42');assert.equal(fw('3.16'),'3.16');assert.equal(fw('03.05'),'3.05');for(const bad of [undefined,'garbage','3',''])assert.equal(fw(bad),'—');
 const a=about({model:'OM4001A',serial:'2302',firmware:'03.42',operating_minutes:55756});
 assert.equal(a.available,true);assert.deepEqual(a.rows,[['Type of PA','OM4001A'],['Amplifier serial no.','2302'],['PA firmware version','3.42'],['Operating time','929h 16m']]);
 assert.equal(about({model:'OM3501A',firmware:'03.25',operating_minutes:5}).rows[1][1],'—');
 for(const none of [null,undefined,{}]){assert.equal(about(none).available,false);assert.deepEqual(about(none).rows,[])}
 console.log('About amplifier checks passed');
}
}

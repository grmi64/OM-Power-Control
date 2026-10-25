const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function page({allowed=true,connected=false,confirm=true,reject=false}={}){
 const nodes={},requests=[],prompts=[],closed=[],node=id=>nodes[id]??={value:'',disabled:false,hidden:false,textContent:''};let tick;
 const context=vm.createContext({document:{getElementById:node},lastState:{connection:connected?'Connected':'Disconnected'},setInterval:fn=>{tick=fn},window:{omAccessMode:{allowed,mode:'simulation',host:'simulation',port:10001},addEventListener(){},close:()=>closed.push(requests.length),confirm:message=>{prompts.push(message);return confirm},pywebview:{api:{request_access_mode:async value=>{requests.push(value);if(reject)throw Error('Disconnect first')}}}}});
 vm.runInContext(fs.readFileSync(__dirname+'/windows_access.js','utf8'),context);
 return {nodes,requests,prompts,closed,tick,context};
}
(async()=>{
 let p=page({connected:true});assert.equal(p.nodes.applyAccessMode.disabled,true);await p.nodes.applyAccessMode.onclick();assert.equal(p.requests.length,0);
 p.context.lastState.connection='Disconnected';p.tick();assert.equal(p.nodes.applyAccessMode.disabled,false);
 for(const mode of ['read-only','hardware']){
  p=page();p.nodes.accessMode.value=mode;p.nodes.accessHost.value='192.0.2.1';p.nodes.accessPort.value='10001';p.nodes.accessMode.onchange();
  assert.equal(p.nodes.accessEndpoint.hidden,false);await p.nodes.applyAccessMode.onclick();
  assert.equal(p.requests[0].mode,mode);assert.equal(p.requests[0].confirmed,true);assert.equal(p.requests[0].port,10001);assert.match(p.prompts[0],/No connection is made until you click Connect/);
  assert.equal(p.nodes.applyAccessMode.disabled,true,'Duplicate handoff blocked');
  assert.equal(p.closed.length,1,'Close requested only after successful bridge reply');
 }
 p=page({confirm:false});p.nodes.accessMode.value='hardware';await p.nodes.applyAccessMode.onclick();assert.equal(p.requests.length,0);
 p=page({allowed:false});await p.nodes.applyAccessMode.onclick();assert.equal(p.requests.length,0);
 p=page({reject:true});await p.nodes.applyAccessMode.onclick();assert.match(p.nodes.accessModeMessage.textContent,/Disconnect first/);assert.equal(p.nodes.applyAccessMode.disabled,false);assert.equal(p.closed.length,0);
 const error=p.nodes.accessModeMessage.textContent;
 for(let i=0;i<5;i++){p.tick();assert.equal(p.nodes.accessModeMessage.textContent,error,'Validation error must survive periodic updates');}
 for(const field of ['accessHost','accessPort','accessMode']){
  p=page({reject:true});await p.nodes.applyAccessMode.onclick();p.tick();
  if(field==='accessMode')p.nodes[field].onchange();else p.nodes[field].oninput();
  p.tick();assert.doesNotMatch(p.nodes.accessModeMessage.textContent,/Disconnect first/,'Editing clears old validation error');
 }
 p=page({reject:true});await p.nodes.applyAccessMode.onclick();
 let finishRetry;
 p.context.window.pywebview.api.request_access_mode=value=>{p.requests.push(value);return new Promise(resolve=>finishRetry=resolve)};
 const retry=p.nodes.applyAccessMode.onclick();p.tick();
 assert.match(p.nodes.accessModeMessage.textContent,/Reopening/,'Retry clears the previous error');
 assert.equal(p.closed.length,0,'Do not close before successful reply');finishRetry({reopening:true});await retry;
 assert.equal(p.closed.length,1);
 p=page();await p.nodes.applyAccessMode.onclick();assert.equal(p.requests[0].mode,'simulation');assert.equal(p.prompts.length,0);
 console.log('Windows access UI: disconnect gate, mode confirmation, cancellation, restricted sessions and handoff errors pass.');
})().catch(error=>{console.error(error);process.exitCode=1});

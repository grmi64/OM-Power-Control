/* Windows native bridge only. No HTTP route can change hardware access policy. */
(()=>{
 const config=window.omAccessMode, panel=document.getElementById('accessModePanel');
 const mode=document.getElementById('accessMode'), host=document.getElementById('accessHost'), port=document.getElementById('accessPort');
 const endpoint=document.getElementById('accessEndpoint'), message=document.getElementById('accessModeMessage'), button=document.getElementById('applyAccessMode');
 let switching=false, errorMessage='';
 mode.value=config.mode;
 host.value=config.host==='simulation'?'':config.host;port.value=String(config.port);
 const descriptions={simulation:'Offline simulation. No amplifier connection.', 'read-only':'Read-only telemetry: operating, tuning and power controls are blocked.', hardware:'Hardware controls: amplifier operating, tuning and power controls are available. You supply/stop RF and set drive power. The app never keys the radio or adjusts drive power.'};
 function update(){
  endpoint.hidden=mode.value==='simulation';
  const disconnected=typeof lastState!=='undefined' && lastState.connection==='Disconnected';
  button.disabled=switching || !config.allowed || !disconnected || !window.pywebview?.api?.request_access_mode;
  if(!switching)message.textContent=errorMessage || (!config.allowed?'Connection-mode changes are unavailable in this restricted test session.':descriptions[mode.value]+(disconnected?' Apply reopens disconnected.':' Disconnect first.'));
 }
 function edited(){errorMessage='';update();}
 mode.onchange=edited;host.oninput=edited;port.oninput=edited;
 button.onclick=async()=>{
  update();if(button.disabled)return;
  errorMessage='';update();
  const selected=mode.value;
  if(selected!=='simulation' && !window.confirm(descriptions[selected]+' Reopen in this mode? No connection is made until you click Connect.'))return;
  switching=true;update();message.textContent='Reopening in the selected mode. No amplifier connection will be made automatically.';
  try{await window.pywebview.api.request_access_mode({mode:selected,host:host.value,port:Number(port.value),confirmed:selected!=='simulation'});window.close();}
  catch(error){switching=false;errorMessage=String(error.message||error);update();}
 };
 window.addEventListener('pywebviewready',update);setInterval(update,500);update();
})();

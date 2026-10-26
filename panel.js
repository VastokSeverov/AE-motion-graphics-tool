/* CEP panel: polls the loopback bridge and executes queued commands in After Effects. */
(function(){
  const base='http://127.0.0.1:8766'; let running=false;
  const state=document.getElementById('state');
  function show(message,good){state.textContent=message;state.className=good?'good':'bad';}
  function postResult(message){fetch(base+'/api/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message})}).catch(()=>{});}
  function escapeForJSX(obj){return JSON.stringify(JSON.stringify(obj));}
  function execute(cmd){
    if(!window.__adobe_cep__ || !window.__adobe_cep__.evalScript){postResult('ERROR: CEP evalScript bridge is unavailable.');return;}
    const jsx='Vasto.executeCommand('+escapeForJSX(cmd)+')';
    window.__adobe_cep__.evalScript(jsx,function(result){
      let message=result||'After Effects returned no result.';
      try{const parsed=JSON.parse(result);message=parsed.message||result;}catch(e){}
      postResult(message);show(message,!/^ERROR|^Error/.test(message));
    });
  }
  async function poll(){if(running)return;running=true;try{const r=await fetch(base+'/api/next',{cache:'no-store'});const d=await r.json();if(d.command){show('Executing: '+d.command.action+'…',true);execute(d.command);}else{show('Connected to local bridge. Waiting for commands from the browser.',true)}}catch(e){show('Bridge offline. Start server/server.py, then reopen this panel. '+e,false)}finally{running=false;}}
  window.checkNow=()=>poll();setInterval(poll,1000);poll();
})();

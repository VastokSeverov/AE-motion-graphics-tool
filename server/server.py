#!/usr/bin/env python3
"""Local command bridge for the VASTOCHNIY After Effects Copilot MVP.
Only binds to loopback. No external network calls or API keys required.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, threading, webbrowser, time

HOST, PORT = '127.0.0.1', 8766
ROOT = Path(__file__).resolve().parent
_lock = threading.Lock()
_queue = []
_results = []

HTML = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VASTOCHNIY AE Copilot</title>
<style>body{font:15px system-ui;background:#101114;color:#f2f2f2;max-width:760px;margin:40px auto;padding:0 18px}h1{font-size:27px}p{color:#b8bac3;line-height:1.5}.card{background:#1b1c21;border:1px solid #34353c;border-radius:14px;padding:18px;margin:16px 0}label{display:block;margin:12px 0 6px;color:#d9d9df}input,select{box-sizing:border-box;width:100%;padding:12px;border-radius:8px;border:1px solid #444650;background:#101114;color:white;font:inherit}button{background:#f0f0f0;color:#111;border:0;border-radius:9px;padding:12px 17px;font-weight:700;cursor:pointer;margin-top:14px}button:disabled{opacity:.45}#status{white-space:pre-wrap;line-height:1.5;color:#d6e8ff}.small{font-size:12px;color:#9b9da7}</style></head><body>
<h1>VASTOCHNIY <span style="color:#a5a6ad">AE Copilot</span></h1><p>Execution test for After Effects. Keep After Effects open, open the installed <b>VASTOCHNIY AE Copilot</b> panel, and make sure the panel says it is connected before sending a command.</p>
<div class="card"><h3>Execute in active composition</h3><label for="action">Action</label><select id="action"><option value="animated_text">Create animated text layer</option><option value="shape">Create shape layer</option><option value="liquid_glass">Create liquid-glass starter shape</option><option value="organize">Organize selected layers (prefix names)</option></select><label for="text">Text / layer name</label><input id="text" value="VASTOCHNIY" maxlength="180"><label for="duration">Animation duration (seconds)</label><input id="duration" type="number" min="0.2" max="5" step="0.1" value="0.8"><button id="send">Send command to After Effects</button><p class="small">This MVP only executes these explicit actions. It does not yet perform AI reference reconstruction, Uzbek proofreading, background removal, or downloading.</p></div>
<div class="card"><h3>Execution log</h3><div id="status">Waiting for the After Effects panel to connect…</div></div>
<script>
const statusEl=document.getElementById('status'),send=document.getElementById('send');let busy=false;
async function refresh(){try{const r=await fetch('/api/status');const d=await r.json();if(!busy)statusEl.textContent=d.panelConnected?'After Effects panel connected. Ready to execute commands.':'Browser server running; waiting for the After Effects panel…';if(d.results?.length){statusEl.textContent=d.results.slice(-5).map(x=>new Date(x.time).toLocaleTimeString()+' — '+x.message).join('\n')}}catch(e){statusEl.textContent='Cannot reach local server: '+e}}
setInterval(refresh,1500);refresh();
send.onclick=async()=>{if(busy)return;busy=true;send.disabled=true;try{const payload={action:document.getElementById('action').value,text:document.getElementById('text').value,duration:Number(document.getElementById('duration').value)};const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();statusEl.textContent=d.message||'Command queued. Waiting for After Effects…';}catch(e){statusEl.textContent='Could not send command: '+e}finally{busy=false;send.disabled=false}};
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, data, code=200):
        raw=json.dumps(data).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Access-Control-Allow-Origin','http://127.0.0.1:8766'); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        global _last_heartbeat
        p=urlparse(self.path).path
        if p=='/':
            raw=HTML.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if p=='/api/status':
            with _lock: results=list(_results); connected=(time.time()-_last_heartbeat<5)
            self.send_json({'ok':True,'panelConnected':connected,'results':results}); return
        if p=='/api/next':
            with _lock:
                _last_heartbeat=time.time()
                item=_queue.pop(0) if _queue else None
            self.send_json({'command':item}); return
        self.send_json({'error':'not found'},404)
    def do_POST(self):
        global _last_heartbeat
        p=urlparse(self.path).path
        try: data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))).decode() or '{}')
        except Exception: self.send_json({'error':'invalid JSON'},400); return
        if p=='/api/command':
            if data.get('action') not in ('animated_text','shape','liquid_glass','organize'):
                self.send_json({'error':'Unsupported action'},400); return
            text=str(data.get('text','VASTOCHNIY'))[:180]
            try: duration=max(.2,min(5,float(data.get('duration',.8))))
            except Exception: duration=.8
            cmd={'id':str(time.time_ns()),'action':data['action'],'text':text,'duration':duration}
            with _lock: _queue.append(cmd)
            self.send_json({'ok':True,'message':'Command queued. After Effects will execute it when the panel is connected.'}); return
        if p=='/api/result':
            with _lock:
                _last_heartbeat=time.time(); _results.append({'time':time.time(),'message':str(data.get('message','No message'))[:500]}); del _results[:-30]
            self.send_json({'ok':True}); return
        self.send_json({'error':'not found'},404)

_last_heartbeat=0

def main():
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f'VASTOCHNIY AE Copilot bridge running at http://{HOST}:{PORT}',flush=True)
    print('Keep this Terminal window open. Press Ctrl+C to stop.',flush=True)
    threading.Timer(1.0,lambda:webbrowser.open(f'http://{HOST}:{PORT}')).start()
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nStopping bridge…')
    finally: server.server_close()
if __name__=='__main__': main()

#!/usr/bin/env python3
"""Local command bridge for VASTOCHNIY AE Copilot.
Loopback-only; no external network calls or API keys.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from collections import deque
import json, threading, webbrowser, time, uuid, sys

HOST, PORT = "127.0.0.1", 8766
_lock = threading.RLock()
_queue = deque()
_commands = {}
_results = deque(maxlen=100)
_inflight_id = None
_last_heartbeat = 0.0
COMMAND_TIMEOUT_SECONDS = 45
ALLOWED_ACTIONS = {"animated_text", "shape", "liquid_glass", "organize"}

HTML = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VASTOCHNIY AE Copilot</title>
<style>
:root{color-scheme:dark}body{font:15px system-ui;background:#101114;color:#f2f2f2;max-width:760px;margin:40px auto;padding:0 18px}h1{font-size:27px}p{color:#b8bac3;line-height:1.5}.card{background:#1b1c21;border:1px solid #34353c;border-radius:14px;padding:18px;margin:16px 0}label{display:block;margin:12px 0 6px;color:#d9d9df}input,select{box-sizing:border-box;width:100%;padding:12px;border-radius:8px;border:1px solid #444650;background:#101114;color:white;font:inherit}button{background:#f0f0f0;color:#111;border:0;border-radius:9px;padding:12px 17px;font-weight:700;cursor:pointer;margin-top:14px}button:disabled{opacity:.45}#status{white-space:pre-wrap;line-height:1.5;color:#d6e8ff}.small{font-size:12px;color:#9b9da7}.warn{color:#ffd18a}
</style></head><body>
<h1>VASTOCHNIY <span style="color:#a5a6ad">AE Copilot</span></h1>
<p>Send explicit commands to the open After Effects composition. Keep the CEP panel open. A running browser server alone does not mean After Effects is connected.</p>
<div class="card"><h3>Execute in active composition</h3>
<label for="action">Action</label><select id="action"><option value="animated_text">Create animated text layer</option><option value="shape">Create rounded rectangle shape</option><option value="liquid_glass">Create liquid-glass starter shape</option><option value="organize">Prefix selected layer names</option></select>
<label for="text">Text / layer name</label><input id="text" value="VASTOCHNIY" maxlength="180">
<label for="duration">Animation duration (seconds)</label><input id="duration" type="number" min="0.2" max="5" step="0.1" value="0.8">
<button id="send">Send command to After Effects</button><p class="small">Actions modify the active composition. Test in a disposable project first.</p></div>
<div class="card"><h3>Connection and execution status</h3><div id="status">Checking local bridge…</div></div>
<div class="card"><h3>Recent execution log</h3><div id="log" class="small">No commands yet.</div></div>
<script>
const statusEl=document.getElementById('status'),logEl=document.getElementById('log'),send=document.getElementById('send');let busy=false;
async function refresh(){try{const r=await fetch('/api/status',{cache:'no-store'});const d=await r.json();const age=d.panelLastSeenSeconds;
statusEl.textContent=d.panelConnected?'After Effects panel is polling the bridge. Last seen '+age+'s ago.':(d.serverRunning?'Bridge running; waiting for the After Effects CEP panel.':'Bridge unavailable.');
if(d.inflight)statusEl.textContent+='\nExecuting command '+d.inflight.id+'…';
if(d.results&&d.results.length)logEl.textContent=d.results.slice(-10).reverse().map(x=>new Date(x.time*1000).toLocaleTimeString()+' — ['+x.status+'] '+x.message).join('\n');
}catch(e){statusEl.textContent='Cannot reach local server: '+e}}
setInterval(refresh,1200);refresh();
send.onclick=async()=>{if(busy)return;busy=true;send.disabled=true;try{
const payload={action:document.getElementById('action').value,text:document.getElementById('text').value,duration:Number(document.getElementById('duration').value)};
const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();
if(!r.ok)throw new Error(d.error||'Command rejected');statusEl.textContent='Queued command '+d.id+'. Waiting for After Effects to report the result…';await refresh();
}catch(e){statusEl.textContent='Could not queue command: '+e.message;}finally{busy=false;send.disabled=false}}
</script></body></html>'''

def _expire_inflight(now=None):
    """Mark timed-out execution as uncertain; never auto-retry side-effecting AE commands."""
    global _inflight_id
    now = time.time() if now is None else now
    if _inflight_id:
        item = _commands.get(_inflight_id)
        if item and item["status"] == "executing" and now - item["started_at"] > COMMAND_TIMEOUT_SECONDS:
            item["status"] = "timeout"
            item["message"] = "Timed out waiting for After Effects. Outcome is unknown; inspect the composition before retrying."
            item["finished_at"] = now
            _results.append({"time": now, "status": "timeout", "message": item["message"], "id": item["id"]})
            _inflight_id = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, data, code=200):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")\n        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")\n        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(raw)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()
    def do_GET(self):
        global _last_heartbeat, _inflight_id
        path = urlparse(self.path).path
        if path == "/":
            raw = HTML.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if path == "/api/status":
            with _lock:
                _expire_inflight()
                age = max(0, round(time.time()-_last_heartbeat, 1)) if _last_heartbeat else None
                active = _commands.get(_inflight_id) if _inflight_id else None
                results = list(_results)
            self.send_json({"ok":True,"serverRunning":True,"panelConnected":age is not None and age < 5,
                            "panelLastSeenSeconds":age,"inflight":({"id":active["id"],"action":active["action"]} if active else None),
                            "results":results}); return
        if path == "/api/next":
            with _lock:
                _last_heartbeat = time.time()
                _expire_inflight()
                # Deliver one command and retain it until the panel reports its final result.
                if _inflight_id:
                    item = _commands.get(_inflight_id)
                    self.send_json({"command":None,"busy":True,"inflightId":_inflight_id}); return
                while _queue:
                    cid = _queue.popleft()
                    item = _commands.get(cid)
                    if item and item["status"] == "queued":
                        item["status"] = "executing"; item["started_at"] = time.time()
                        _inflight_id = cid
                        self.send_json({"command":{"id":item["id"],"action":item["action"],"text":item["text"],"prefix":item["prefix"],"duration":item["duration"]}}); return
            self.send_json({"command":None,"busy":False}); return
        self.send_json({"error":"not found"},404)
    def do_POST(self):
        global _last_heartbeat, _inflight_id
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length","0"))
            if length < 0 or length > 16384: raise ValueError("request too large")
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(data, dict): raise ValueError("JSON object required")
        except Exception:
            self.send_json({"error":"invalid JSON or request size"},400); return
        if path == "/api/command":
            action = data.get("action")
            if action not in ALLOWED_ACTIONS:
                self.send_json({"error":"Unsupported action"},400); return
            text = str(data.get("text","VASTOCHNIY"))[:180]
            try: duration = max(.2,min(5,float(data.get("duration",.8))))
            except (TypeError,ValueError): duration = .8
            item={"id":uuid.uuid4().hex,"action":action,"text":text,"prefix":prefix,"duration":duration,"status":"queued","created_at":time.time()}
            with _lock:
                _commands[item["id"]]=item; _queue.append(item["id"])
            self.send_json({"ok":True,"id":item["id"],"status":"queued","message":"Command queued."},202); return
        if path == "/api/result":
            cid = str(data.get("id",""))
            message = str(data.get("message","No message"))[:500]
            explicit_status = data.get("status")
            if explicit_status not in ("succeeded","failed"): explicit_status = "failed" if message.upper().startswith("ERROR") else "succeeded"
            with _lock:
                _last_heartbeat = time.time()
                item = _commands.get(cid)
                if not item:
                    self.send_json({"error":"unknown command id"},404); return
                if item["status"] in ("succeeded","failed","timeout"):
                    self.send_json({"ok":True,"duplicate":True,"status":item["status"]}); return
                if item["status"] != "executing" or _inflight_id != cid:
                    self.send_json({"error":"command is not the active execution"},409); return
                item["status"] = explicit_status; item["message"] = message; item["finished_at"] = time.time()
                _results.append({"time":item["finished_at"],"status":explicit_status,"message":message,"id":cid})
                _inflight_id = None
            self.send_json({"ok":True,"status":explicit_status}); return
        self.send_json({"error":"not found"},404)

def main():
    server = ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"VASTOCHNIY AE Copilot bridge running at http://{HOST}:{PORT}",flush=True)
    print("Keep this Terminal window open. Press Ctrl+C to stop.",flush=True)
    if "--open-browser" in sys.argv:\n        threading.Timer(1.0,lambda:webbrowser.open(f"http://{HOST}:{PORT}")).start()
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStopping bridge…")
    finally: server.server_close()
if __name__ == "__main__": main()

/* VASTOCHNIY AE Copilot — background-removal-only panel. */
(function () {
  'use strict';
  var base = 'http://127.0.0.1:8766';
  var button = document.getElementById('removeBackground');
  var statusEl = document.getElementById('status');
  var connectionEl = document.getElementById('connection');
  var busy = false;

  function show(message, good) {
    statusEl.textContent = message;
    statusEl.className = good ? 'good' : 'bad';
  }
  function connection(message, good) {
    connectionEl.textContent = message;
    connectionEl.className = good ? 'good' : 'bad';
  }
  function parseResult(raw) {
    if (!raw || raw === 'EvalScript error.') throw new Error('After Effects did not run the script. Check that the extension is loaded correctly, then restart After Effects.');
    var value;
    try { value = JSON.parse(raw); } catch (_) { throw new Error('Unexpected response from After Effects: ' + raw); }
    if (value.error) throw new Error(value.error);
    return value;
  }
  function evalScript(script, timeoutMs) {
    return new Promise(function (resolve, reject) {
      if (!window.__adobe_cep__ || typeof window.__adobe_cep__.evalScript !== 'function') {
        reject(new Error('After Effects scripting is unavailable. Open this panel inside After Effects, not in a browser.'));
        return;
      }
      var settled = false;
      var timer = setTimeout(function () {
        if (settled) return;
        settled = true;
        reject(new Error('Timed out waiting for After Effects scripting. Restart After Effects and try again.'));
      }, timeoutMs || 30000);
      try {
        window.__adobe_cep__.evalScript(script, function (result) {
          if (settled) return;
          settled = true; clearTimeout(timer);
          try { resolve(parseResult(result)); } catch (err) { reject(err); }
        });
      } catch (err) {
        if (!settled) { settled = true; clearTimeout(timer); reject(err); }
      }
    });
  }
  async function jsonFetch(url, options, timeoutMs) {
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = setTimeout(function () { if (controller) controller.abort(); }, timeoutMs || 600000);
    if (controller) options.signal = controller.signal;
    try {
      var response = await fetch(url, options);
      var data;
      try { data = await response.json(); }
      catch (_) { throw new Error('Bridge returned invalid JSON (HTTP ' + response.status + '). Check the bridge Terminal.'); }
      if (!response.ok) throw new Error(data.error || ('Bridge error (HTTP ' + response.status + ')'));
      return data;
    } catch (err) {
      if (err.name === 'AbortError') throw new Error('Background removal timed out. Check the bridge Terminal; the model may still be downloading.');
      if (err instanceof TypeError) throw new Error('Cannot reach the local bridge. Stop old bridge processes, activate .venv, and run python server/server.py.');
      throw err;
    } finally { clearTimeout(timer); }
  }
  async function checkBridge() {
    try {
      var response = await fetch(base + '/api/status', { cache: 'no-store' });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var data = await response.json();
      connection(data.bridgeReady ? 'Bridge ready' : 'Bridge issue', !!data.bridgeReady);
      if (!busy && data.bridgeReady) show('Ready. Select one still image layer, then click Remove Background.', true);
    } catch (_) {
      connection('Offline', false);
      if (!busy) show('Local bridge is offline. Start it from the repository using the activated .venv: python server/server.py', false);
    }
  }
  button.addEventListener('click', async function () {
    if (busy) return;
    busy = true; button.disabled = true;
    try {
      show('Checking your selected layer in After Effects…', true);
      var info = await evalScript('Vasto.getSelectedImageInfo()', 30000);
      if (!info.path) throw new Error('After Effects did not return an image path. Select one local still-image layer.');
      show('Removing background locally. First run may take several minutes to download the model. Do not close the bridge Terminal…', true);
      var result = await jsonFetch(base + '/api/remove-background', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: info.path })
      }, 900000);
      if (!result.output_path) throw new Error('Bridge finished without returning a transparent PNG path.');
      show('Background removed. Replacing the selected layer source…', true);
      var replaced = await evalScript('Vasto.replaceSelectedImageSource(' + JSON.stringify(result.output_path) + ',' + JSON.stringify(info.path) + ')', 30000);
      show(replaced.message || 'Background removed successfully.', true);
    } catch (err) {
      show('Background removal failed: ' + (err && err.message ? err.message : String(err)), false);
    } finally {
      busy = false; button.disabled = false;
      checkBridge();
    }
  });
  checkBridge();
  setInterval(checkBridge, 4000);
})();
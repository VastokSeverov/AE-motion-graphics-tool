/* CEP panel: serially polls the bridge and waits for AE's callback before polling again. */
(function () {
  var base = 'http://127.0.0.1:8766';
  var running = false;
  var stopped = false;
  var state = document.getElementById('state');

  function show(message, good) {
    state.textContent = message;
    state.className = good ? 'good' : 'bad';
  }
  function postResult(id, message) {
    var status = /^ERROR|^Error/.test(message) ? 'failed' : 'succeeded';
    return fetch(base + '/api/result', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id, message: message, status: status })
    }).then(function (r) {
      if (!r.ok) throw new Error('Bridge rejected execution result (' + r.status + ')');
      return r.json();
    });
  }
  function escapeForJSX(obj) { return JSON.stringify(JSON.stringify(obj)); }

  function execute(cmd) {
    return new Promise(function (resolve) {
      if (!window.__adobe_cep__ || !window.__adobe_cep__.evalScript) {
        postResult(cmd.id, 'ERROR: CEP evalScript bridge is unavailable.').then(resolve).catch(function () { resolve(); });
        return;
      }
      var completed = false;
      var watchdog = setTimeout(function () {
        if (completed) return;
        completed = true;
        // Do not report a definitive failure after a local timeout: AE may still finish.
        show('Timed out waiting for After Effects callback. Check the composition before retrying.', false);
        resolve();
      }, 50000);
      try {
        var jsx = 'Vasto.executeCommand(' + escapeForJSX(cmd) + ')';
        window.__adobe_cep__.evalScript(jsx, function (result) {
          if (completed) return;
          completed = true;
          clearTimeout(watchdog);
          var message = result || 'ERROR: After Effects returned no result.';
          try {
            var parsed = JSON.parse(result);
            message = parsed.message || result;
          } catch (e) {}
          postResult(cmd.id, message).then(function () {
            show(message, !/^ERROR|^Error/.test(message));
          }).catch(function (err) {
            show('AE responded, but the bridge could not record the result: ' + err.message, false);
          }).finally(resolve);
        });
      } catch (e) {
        clearTimeout(watchdog);
        postResult(cmd.id, 'ERROR: Could not invoke After Effects: ' + e.toString())
          .then(function () { show('Could not invoke After Effects: ' + e.toString(), false); })
          .catch(function () {})
          .finally(resolve);
      }
    });
  }

  async function poll() {
    if (running || stopped) return;
    running = true;
    try {
      var response = await fetch(base + '/api/next', { cache: 'no-store' });
      if (!response.ok) throw new Error('Bridge returned HTTP ' + response.status);
      var data = await response.json();
      if (data.command) {
        show('Executing ' + data.command.action + '…', true);
        await execute(data.command);
      } else {
        show('Connected to local bridge. ' + (data.busy ? 'Another command is executing.' : 'Waiting for commands.'), true);
      }
    } catch (e) {
      show('Bridge offline or unreachable. Start server/server.py. ' + e.message, false);
    } finally {
      running = false;
    }
  }
  window.checkNow = function () { poll(); };
  window.stopCopilotPolling = function () { stopped = true; };
  setInterval(poll, 1000);
  poll();
})();

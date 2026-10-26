/* VASTOCHNIY AE Copilot CEP panel: UI, polling, and serialized command execution. */
(function () {
  var base = 'http://127.0.0.1:8766';
  var running = false;
  var busyCommand = false;
  var statusEl = document.getElementById('status');
  var connectionEl = document.getElementById('connection');
  var logEl = document.getElementById('log');
  var actionButtons = document.querySelectorAll('[data-action]');

  function show(message, good) {
    statusEl.textContent = message;
    statusEl.className = good ? 'good' : 'bad';
  }
  function setConnection(message, good) {
    connectionEl.textContent = message;
    connectionEl.className = good ? 'good' : 'bad';
  }
  function setButtonsDisabled(disabled) {
  
  var plannedRequest = null;
  var planButton = document.getElementById('planRequest');
  var runPlanButton = document.getElementById('runPlan');
  var planPreview = document.getElementById('planPreview');

  planButton.addEventListener('click', function () {
    var prompt = document.getElementById('prompt').value;
    if (busyCommand) return;
    planButton.disabled = true;
    runPlanButton.disabled = true;
    plannedRequest = null;
    planPreview.hidden = false;
    planPreview.textContent = 'Planning request…';
    fetch(base + '/api/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt })
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.error || 'Could not plan request');
        plannedRequest = data.plan;
        var actionName = plannedRequest.action.replace(/_/g, ' ');
        planPreview.textContent = 'PROPOSED ACTION: ' + actionName +
          '\\nText: ' + plannedRequest.text +
          '\\nPrefix: ' + plannedRequest.prefix +
          '\\nDuration: ' + plannedRequest.duration + 's' +
          '\\n\\n' + plannedRequest.explanation +
          '\\n\\nNothing has changed yet. Click “Review & Run” to execute this plan.';
        runPlanButton.disabled = false;
        show('Plan ready. Review it before execution.', true);
      });
    }).catch(function (error) {
      planPreview.textContent = error.message;
      show('Planning failed: ' + error.message, false);
    }).finally(function () {
      planButton.disabled = false;
    });
  });

  runPlanButton.addEventListener('click', function () {
    if (!plannedRequest || busyCommand) return;
    var plan = plannedRequest;
    plannedRequest = null;
    runPlanButton.disabled = true;
    document.getElementById('text').value = plan.text;
    document.getElementById('prefix').value = plan.prefix;
    document.getElementById('duration').value = plan.duration;
    planPreview.textContent += '\\n\\nExecuting reviewed plan…';
    queueAction(plan.action);
  });

  Array.prototype.forEach.call(actionButtons, function (button) { button.disabled = disabled; });
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
        show('Timed out waiting for After Effects. Check the composition before retrying.', false);
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

  function updateLog(results) {
    if (!results || !results.length) return;
    logEl.textContent = results.slice(-8).reverse().map(function (item) {
      return new Date(item.time * 1000).toLocaleTimeString() + ' — [' + item.status + '] ' + item.message;
    }).join('\n');
  }

  async function refreshStatus() {
    try {
      var response = await fetch(base + '/api/status', { cache: 'no-store' });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var data = await response.json();
      if (data.panelConnected) setConnection('Connected', true);
      else setConnection('Bridge ready · waiting', false);
      updateLog(data.results);
    } catch (e) {
      setConnection('Offline', false);
      if (!busyCommand) show('Cannot reach local bridge. Start server/server.py. ' + e.message, false);
    }
  }

  async function poll() {
    if (running) return;
    running = true;
    try {
      var response = await fetch(base + '/api/next', { cache: 'no-store' });
      if (!response.ok) throw new Error('Bridge returned HTTP ' + response.status);
      var data = await response.json();
      if (data.command) {
        busyCommand = true;
        setButtonsDisabled(true);
        show('Executing ' + data.command.action.replace(/_/g, ' ') + '…', true);
        await execute(data.command);
        busyCommand = false;
        setButtonsDisabled(false);
        await refreshStatus();
      } else if (!busyCommand) {
        show('Connected. Ready for an action.', true);
      }
    } catch (e) {
      setConnection('Offline', false);
      if (!busyCommand) show('Bridge offline or unreachable. Start server/server.py. ' + e.message, false);
    } finally {
      running = false;
    }
  }

  function queueAction(action) {
    if (busyCommand) return;
    var payload = {
      action: action,
      text: document.getElementById('text').value,
      prefix: document.getElementById('prefix').value,
      duration: Number(document.getElementById('duration').value)
    };
    busyCommand = true;
    setButtonsDisabled(true);
    show('Sending ' + action.replace(/_/g, ' ') + ' to After Effects…', true);
    fetch(base + '/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.error || 'Command rejected');
        show('Command queued. Waiting for After Effects…', true);
      });
    }).catch(function (e) {
      busyCommand = false;
      setButtonsDisabled(false);
      show('Could not queue command: ' + e.message, false);
    });
  }

  Array.prototype.forEach.call(actionButtons, function (button) {
    button.addEventListener('click', function () { queueAction(button.getAttribute('data-action')); });
  });

  // The panel is the command client; the browser UI is no longer required.
  setInterval(function () {
    if (!busyCommand) refreshStatus();
    poll();
  }, 1000);
  refreshStatus();
  poll();
})();
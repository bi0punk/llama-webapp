(function () {
  const output = document.getElementById('output');
  const promptEl = document.getElementById('prompt');
  const sendBtn = document.getElementById('send');
  const clearBtn = document.getElementById('clear');

  function append(txt) {
    output.textContent += txt;
    output.scrollTop = output.scrollHeight;
  }

  function getParams() {
    return {
      threads: Number(document.getElementById('threads').value || 6),
      temp: Number(document.getElementById('temp').value || 0.8),
      ctx: Number(document.getElementById('ctx').value || 2048),
    };
  }

  const proto = (location.protocol === 'https:') ? 'wss' : 'ws';
  const wsUrl = `${proto}://${location.host}/ws/chat`;
  let ws = null;

  function ensureWs() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    ws = new WebSocket(wsUrl);
    ws.onopen = () => append('[ws] conectado\n');
    ws.onclose = () => append('\n[ws] desconectado\n');
    ws.onerror = () => append('\n[ws] error\n');
    ws.onmessage = (ev) => append(ev.data);
  }

  async function send() {
    ensureWs();
    const modelId = Number(document.getElementById('model_id').value || 0);
    const prompt = (promptEl.value || '').trim();
    if (!prompt) {
      append('[!] prompt vacío\n');
      return;
    }

    const payload = {
      model_id: modelId,
      prompt: prompt,
      params: getParams(),
    };

    // wait until open
    for (let i = 0; i < 40; i++) {
      if (ws.readyState === WebSocket.OPEN) break;
      await new Promise(r => setTimeout(r, 50));
    }

    if (ws.readyState !== WebSocket.OPEN) {
      append('[!] websocket no listo\n');
      return;
    }

    append(`\n>>> ${prompt}\n`);
    ws.send(JSON.stringify(payload));
  }

  sendBtn.addEventListener('click', send);
  clearBtn.addEventListener('click', () => { output.textContent = ''; });

  // Ctrl+Enter to send
  promptEl.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') send();
  });

  ensureWs();
})();

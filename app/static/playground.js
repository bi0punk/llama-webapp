(function () {
  const promptEl = document.getElementById('prompt');
  const temperatureEl = document.getElementById('temperature');
  const maxTokensEl = document.getElementById('max_tokens');
  const outputEl = document.getElementById('output');
  const sendBtn = document.getElementById('send');

  async function send() {
    outputEl.textContent = 'Consultando...';
    const payload = {
      prompt: (promptEl.value || '').trim(),
      temperature: Number(temperatureEl.value || 0.2),
      max_tokens: Number(maxTokensEl.value || 256),
    };

    const response = await fetch('/api/playground/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    outputEl.textContent = JSON.stringify(data, null, 2);
  }

  sendBtn.addEventListener('click', send);
})();

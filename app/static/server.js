(function () {
  const logEl = document.getElementById('server-log-tail');
  const modelSelect = document.getElementById('model-select');
  const profileBox = document.getElementById('model-profile-box');
  const profileModelId = document.getElementById('profile-model-id');
  const profiles = window.SERVER_PROFILES || {};

  function renderProfile() {
    if (!modelSelect || !profileBox) return;
    const id = modelSelect.value;
    if (profileModelId) profileModelId.value = id;
    const p = profiles[id];
    if (!p) {
      profileBox.innerHTML = '<div class="small-muted">Sin sugerencia disponible para este modelo.</div>';
      return;
    }
    const notes = (p.notes || []).map((n) => `<div>• ${n}</div>`).join('');
    profileBox.innerHTML = `
      <div class="fw-semibold text-dark mb-2">Sugerencia para el modelo seleccionado</div>
      <ul class="mb-2">
        <li><span class="mono">threads=${p.threads}</span></li>
        <li><span class="mono">ctx_size=${p.ctx_size}</span></li>
        <li><span class="mono">n_gpu_layers=${p.n_gpu_layers}</span></li>
        <li><span class="mono">extra_args=${p.extra_args}</span></li>
      </ul>
      <div>${notes}</div>
    `;
  }

  async function refreshLog() {
    if (!logEl) return;
    try {
      const response = await fetch('/api/server/log_tail?lines=180');
      const data = await response.json();
      const shouldStick = Math.abs(logEl.scrollHeight - logEl.clientHeight - logEl.scrollTop) < 30;
      logEl.textContent = data.tail || '';
      if (shouldStick) {
        logEl.scrollTop = logEl.scrollHeight;
      }
    } catch (err) {
      console.error(err);
    }
  }

  if (modelSelect) {
    modelSelect.addEventListener('change', renderProfile);
    renderProfile();
  }

  refreshLog();
  setInterval(refreshLog, 3000);
})();

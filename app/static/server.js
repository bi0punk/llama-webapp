(function () {
  const logEl = document.getElementById('server-log-tail');
  const modelSelect = document.getElementById('model-select');
  const profileBox = document.getElementById('model-profile-box');
  const profileModelId = document.getElementById('profile-model-id');
  const backendSelect = document.getElementById('backend-select');
  const llamaGroup = document.getElementById('llama-model-group');
  const unifiedGroup = document.getElementById('unified-model-group');
  const unifiedSelect = document.getElementById('unified-model-select');
  const startBtn = document.getElementById('start-btn');
  const profiles = window.SERVER_PROFILES || {};

  function toggleBackend() {
    const backend = backendSelect ? backendSelect.value : 'llama_server';
    if (llamaGroup) llamaGroup.style.display = backend === 'llama_server' ? '' : 'none';
    if (unifiedGroup) unifiedGroup.style.display = backend === 'llama_unified' ? '' : 'none';
    if (startBtn) startBtn.textContent = backend === 'llama_unified' ? 'Iniciar llama (unified)' : 'Iniciar llama-server';
    renderProfile();
  }

  function renderProfile() {
    if (!profileBox) return;
    const backend = backendSelect ? backendSelect.value : 'llama_server';
    if (backend === 'llama_unified') {
      profileBox.innerHTML = '<div class="small-muted">Usando binario unificado llama. Selecciona el modelo GGUF abajo.</div>';
      return;
    }
    const id = modelSelect ? modelSelect.value : '';
    if (profileModelId) profileModelId.value = id;
    const p = profiles[id];
    if (!p) {
      profileBox.innerHTML = '<div class="small-muted">Sin sugerencia disponible para este modelo.</div>';
      return;
    }
    const notes = (p.notes || []).map(function (n) { return '<div>\u2022 ' + n + '</div>'; }).join('');
    profileBox.innerHTML = [
      '<div class="fw-semibold text-dark mb-2">Sugerencia para el modelo seleccionado</div>',
      '<ul class="mb-2">',
      '<li><span class="mono">threads=' + p.threads + '</span></li>',
      '<li><span class="mono">ctx_size=' + p.ctx_size + '</span></li>',
      '<li><span class="mono">n_gpu_layers=' + p.n_gpu_layers + '</span></li>',
      '<li><span class="mono">extra_args=' + p.extra_args + '</span></li>',
      '</ul><div>' + notes + '</div>',
    ].join('');
  }

  async function refreshLog() {
    if (!logEl) return;
    try {
      var response = await fetch('/api/server/log_tail?lines=180');
      var data = await response.json();
      var shouldStick = Math.abs(logEl.scrollHeight - logEl.clientHeight - logEl.scrollTop) < 30;
      logEl.textContent = data.tail || '';
      if (shouldStick) logEl.scrollTop = logEl.scrollHeight;
    } catch (err) {
      console.error(err);
    }
  }

  if (modelSelect) {
    modelSelect.addEventListener('change', renderProfile);
  }
  if (backendSelect) {
    backendSelect.addEventListener('change', toggleBackend);
  }

  toggleBackend();
  renderProfile();
  refreshLog();
  setInterval(refreshLog, 3000);
})();

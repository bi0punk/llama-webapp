import type { ModelProfile, ServerLogResponse } from "./types.js";

function getEl<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

function renderProfile(profiles: Record<number, ModelProfile>): void {
  const modelSelect = getEl<HTMLSelectElement>("model-select");
  const profileBox = getEl<HTMLElement>("model-profile-box");
  const profileModelId = getEl<HTMLInputElement>("profile-model-id");
  if (!modelSelect || !profileBox) return;

  const id = modelSelect.value;
  if (profileModelId) profileModelId.value = id;
  const p = profiles[Number(id)];
  if (!p) {
    profileBox.innerHTML = '<div class="small-muted">Sin sugerencia disponible para este modelo.</div>';
    return;
  }
  const notes = (p.notes || []).map((n) => `<div>\u2022 ${n}</div>`).join("");
  profileBox.innerHTML = [
    '<div class="fw-semibold text-dark mb-2">Sugerencia para el modelo seleccionado</div>',
    '<ul class="mb-2">',
    `<li><span class="mono">threads=${p.threads}</span></li>`,
    `<li><span class="mono">ctx_size=${p.ctx_size}</span></li>`,
    `<li><span class="mono">n_gpu_layers=${p.n_gpu_layers}</span></li>`,
    `<li><span class="mono">extra_args=${p.extra_args}</span></li>`,
    "</ul><div>" + notes + "</div>",
  ].join("");
}

async function refreshLog(): Promise<void> {
  const logEl = getEl<HTMLElement>("server-log-tail");
  if (!logEl) return;
  try {
    const response = await fetch("/api/server/log_tail?lines=180");
    const data: ServerLogResponse = await response.json();
    const shouldStick = Math.abs(logEl.scrollHeight - logEl.clientHeight - logEl.scrollTop) < 30;
    logEl.textContent = data.tail || "";
    if (shouldStick) logEl.scrollTop = logEl.scrollHeight;
  } catch (err) {
    console.error(err);
  }
}

function init(): void {
  const profiles = window.SERVER_PROFILES ?? {};
  const modelSelect = getEl<HTMLSelectElement>("model-select");
  if (modelSelect) {
    modelSelect.addEventListener("change", () => renderProfile(profiles));
    renderProfile(profiles);
  }
  refreshLog();
  setInterval(refreshLog, 3000);
}

init();

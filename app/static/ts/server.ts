import type { LogStreamEvent, ModelProfile, ServerMetrics } from "./types.js";

function getEl<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

function fmtBytes(bytes: number | null | undefined): string {
  if (!bytes) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[unit]}`;
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

async function refreshMetrics(): Promise<void> {
  const el = getEl<HTMLElement>("server-metrics");
  if (!el) return;
  try {
    const response = await fetch("/api/server/metrics");
    const metrics: ServerMetrics = await response.json();
    if (!metrics.running || !metrics.process) {
      el.textContent = "Detenido";
      return;
    }
    const llama = metrics.llama ?? {};
    const slots = llama.slots_processing != null
      ? ` · slots ${llama.slots_idle ?? "?"}/${llama.slots_processing}`
      : "";
    el.textContent = `CPU ${metrics.process.cpu_percent}% · RAM ${fmtBytes(metrics.process.rss_bytes)}${slots}`;
  } catch (err) {
    console.error(err);
  }
}

function initLogStream(): void {
  const logEl = getEl<HTMLElement>("server-log-tail");
  if (!logEl || !window.EventSource) return;
  const source = new EventSource("/api/server/log_stream");
  let started = false;
  source.onmessage = (event: MessageEvent<string>) => {
    try {
      const data: LogStreamEvent = JSON.parse(event.data);
      if (!data.text) return;
      const shouldStick = Math.abs(logEl.scrollHeight - logEl.clientHeight - logEl.scrollTop) < 30;
      if (!started) {
        logEl.textContent = data.text;
        started = true;
      } else {
        logEl.textContent += data.text;
      }
      if (shouldStick) logEl.scrollTop = logEl.scrollHeight;
    } catch (err) {
      console.error(err);
    }
  };
  source.onerror = () => {
    started = false;
    setTimeout(() => {
      source.close();
      initLogStream();
    }, 3000);
  };
}

function init(): void {
  const profiles = window.SERVER_PROFILES ?? {};
  const modelSelect = getEl<HTMLSelectElement>("model-select");
  if (modelSelect) {
    modelSelect.addEventListener("change", () => renderProfile(profiles));
    renderProfile(profiles);
  }
  refreshMetrics();
  setInterval(refreshMetrics, 3000);
  initLogStream();
}

init();
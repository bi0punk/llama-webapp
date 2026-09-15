function getEl(id) {
    return document.getElementById(id);
}
function fmtBytes(bytes) {
    if (!bytes)
        return "-";
    const units = ["B", "KB", "MB", "GB"];
    let value = bytes;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
        value /= 1024;
        unit += 1;
    }
    return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[unit]}`;
}
function renderProfile(profiles) {
    const modelSelect = getEl("model-select");
    const profileBox = getEl("model-profile-box");
    const profileModelId = getEl("profile-model-id");
    if (!modelSelect || !profileBox)
        return;
    const id = modelSelect.value;
    if (profileModelId)
        profileModelId.value = id;
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
async function refreshMetrics() {
    const el = getEl("server-metrics");
    if (!el)
        return;
    try {
        const response = await fetch("/api/server/metrics");
        const metrics = await response.json();
        if (!metrics.running || !metrics.process) {
            el.textContent = "Detenido";
            return;
        }
        const llama = metrics.llama ?? {};
        const slots = llama.slots_processing != null
            ? ` · slots ${llama.slots_idle ?? "?"}/${llama.slots_processing}`
            : "";
        el.textContent = `CPU ${metrics.process.cpu_percent}% · RAM ${fmtBytes(metrics.process.rss_bytes)}${slots}`;
    }
    catch (err) {
        console.error(err);
    }
}
function initLogStream() {
    const logEl = getEl("server-log-tail");
    if (!logEl || !window.EventSource)
        return;
    const source = new EventSource("/api/server/log_stream");
    let started = false;
    source.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (!data.text)
                return;
            const shouldStick = Math.abs(logEl.scrollHeight - logEl.clientHeight - logEl.scrollTop) < 30;
            if (!started) {
                logEl.textContent = data.text;
                started = true;
            }
            else {
                logEl.textContent += data.text;
            }
            if (shouldStick)
                logEl.scrollTop = logEl.scrollHeight;
        }
        catch (err) {
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
function init() {
    const profiles = window.SERVER_PROFILES ?? {};
    const modelSelect = getEl("model-select");
    if (modelSelect) {
        modelSelect.addEventListener("change", () => renderProfile(profiles));
        renderProfile(profiles);
    }
    refreshMetrics();
    setInterval(refreshMetrics, 3000);
    initLogStream();
}
init();
export {};
//# sourceMappingURL=server.js.map
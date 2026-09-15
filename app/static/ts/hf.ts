interface HfSearchResult {
  id: string;
  downloads: number;
  likes: number;
  tags: string[];
}

interface HfSearchResponse {
  query: string;
  results: HfSearchResult[];
}

interface HfFilesResponse {
  repo: string;
  files: string[];
}

function getEl<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

function fmtNum(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function downloadForm(repo: string, file: string): HTMLFormElement {
  const form = document.createElement("form");
  form.method = "post";
  form.action = "/models/add_and_download";
  form.className = "d-inline";

  const name = document.createElement("input");
  name.type = "hidden";
  name.name = "name";
  name.value = file.split("/").pop() ?? file;
  form.appendChild(name);

  const url = document.createElement("input");
  url.type = "hidden";
  url.name = "url";
  url.value = `https://huggingface.co/${repo}/resolve/main/${file}`;
  form.appendChild(url);

  const source = document.createElement("input");
  source.type = "hidden";
  source.name = "source_type";
  source.value = "direct_url";
  form.appendChild(source);

  const button = document.createElement("button");
  button.className = "btn btn-sm btn-outline-success";
  button.textContent = "Descargar";
  form.appendChild(button);
  return form;
}

async function loadFiles(repo: string): Promise<void> {
  const container = getEl<HTMLElement>("hf-files");
  if (!container) return;
  container.innerHTML = '<div class="small-muted">Cargando archivos .gguf…</div>';
  try {
    const response = await fetch(`/api/hf/files?repo=${encodeURIComponent(repo)}`);
    const data: HfFilesResponse = await response.json();
    if (!data.files.length) {
      container.innerHTML = '<div class="small-muted">Sin archivos .gguf en este repo.</div>';
      return;
    }
    container.innerHTML = "";
    for (const file of data.files) {
      const row = document.createElement("div");
      row.className = "d-flex align-items-center justify-content-between mb-1";
      const label = document.createElement("span");
      label.className = "mono small";
      label.textContent = file;
      row.appendChild(label);
      row.appendChild(downloadForm(repo, file));
      container.appendChild(row);
    }
  } catch (err) {
    console.error(err);
    container.innerHTML = '<div class="text-danger small">Error consultando HuggingFace.</div>';
  }
}

function renderResults(results: HfSearchResult[], box: HTMLElement): void {
  if (!results.length) {
    box.innerHTML = '<div class="small-muted">Sin resultados.</div>';
    return;
  }
  box.innerHTML = "";
  for (const r of results) {
    const item = document.createElement("div");
    item.className = "border rounded p-2 mb-2";
    const head = document.createElement("div");
    head.className = "d-flex justify-content-between align-items-center";
    const title = document.createElement("span");
    title.className = "fw-semibold mono small";
    title.textContent = r.id;
    head.appendChild(title);
    const meta = document.createElement("span");
    meta.className = "small-muted small";
    meta.textContent = `${fmtNum(r.downloads)} descargas · ${fmtNum(r.likes)} likes`;
    head.appendChild(meta);
    item.appendChild(head);

    const tags = (r.tags || []).slice(0, 3);
    if (tags.length) {
      const tagBox = document.createElement("div");
      tagBox.className = "mt-1";
      for (const t of tags) {
        const badge = document.createElement("span");
        badge.className = "badge text-bg-light border me-1";
        badge.textContent = t;
        tagBox.appendChild(badge);
      }
      item.appendChild(tagBox);
    }

    const actions = document.createElement("div");
    actions.className = "mt-2 d-flex align-items-center gap-2";
    const showFiles = document.createElement("button");
    showFiles.className = "btn btn-sm btn-outline-dark";
    showFiles.textContent = "Ver archivos .gguf";
    showFiles.addEventListener("click", () => void loadFiles(r.id));
    actions.appendChild(showFiles);
    item.appendChild(actions);
    box.appendChild(item);
  }
}

function init(): void {
  const input = getEl<HTMLInputElement>("hf-search-input");
  const button = getEl<HTMLButtonElement>("hf-search-button");
  const box = getEl<HTMLElement>("hf-results");
  if (!input || !button || !box) return;

  const run = async (): Promise<void> => {
    const query = input.value.trim();
    if (!query) return;
    box.innerHTML = '<div class="small-muted">Buscando…</div>';
    const filesBox = getEl<HTMLElement>("hf-files");
    if (filesBox) filesBox.innerHTML = "";
    try {
      const response = await fetch(`/api/hf/search?q=${encodeURIComponent(query)}&limit=10`);
      const data: HfSearchResponse = await response.json();
      renderResults(data.results, box);
    } catch (err) {
      console.error(err);
      box.innerHTML = '<div class="text-danger small">Error buscando en HuggingFace.</div>';
    }
  };

  button.addEventListener("click", () => void run());
  input.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void run();
    }
  });
}

init();
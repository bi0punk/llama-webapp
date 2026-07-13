import type { ChatRequest, StreamEvent } from "./types.js";

function getEl<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

async function sendNonStream(payload: ChatRequest): Promise<void> {
  const outputEl = getEl<HTMLElement>("output");
  if (!outputEl) return;
  outputEl.textContent = "Consultando...";
  const response = await fetch("/api/playground/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  outputEl.textContent = JSON.stringify(data, null, 2);
}

async function sendStream(payload: ChatRequest): Promise<void> {
  const outputEl = getEl<HTMLElement>("output");
  if (!outputEl) return;
  outputEl.textContent = "";

  const response = await fetch("/api/playground/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    outputEl.textContent = `Error: ${response.status} ${response.statusText}`;
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();

  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith(":")) continue;
      if (trimmed.startsWith("data: ")) {
        const jsonStr = trimmed.slice(6);
        try {
          const event: StreamEvent = JSON.parse(jsonStr);
          if (event.error) {
            outputEl.textContent += `\nError: ${event.error}`;
            continue;
          }
          const content = event.choices?.[0]?.delta?.content ?? "";
          outputEl.textContent += content;
        } catch {
          // ignore parse errors for partial chunks
        }
      }
    }
  }
}

async function send(): Promise<void> {
  const promptEl = getEl<HTMLTextAreaElement>("prompt");
  const temperatureEl = getEl<HTMLInputElement>("temperature");
  const maxTokensEl = getEl<HTMLInputElement>("max_tokens");
  const streamCheck = getEl<HTMLInputElement>("stream-check");
  if (!promptEl || !temperatureEl || !maxTokensEl) return;
  const payload: ChatRequest = {
    prompt: promptEl.value.trim(),
    temperature: Number(temperatureEl.value || 0.2),
    max_tokens: Number(maxTokensEl.value || 256),
  };
  if (streamCheck?.checked) {
    await sendStream(payload);
  } else {
    await sendNonStream(payload);
  }
}

function init(): void {
  const sendBtn = getEl<HTMLButtonElement>("send");
  sendBtn?.addEventListener("click", send);
}

init();

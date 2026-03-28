const form = document.getElementById('chat-form');
const messageEl = document.getElementById('message');
const statusEl = document.getElementById('status');
const messagesEl = document.getElementById('messages');
const routePillsEl = document.getElementById('route-pills');
const routeSummaryEl = document.getElementById('route-summary');
const sessionIdEl = document.getElementById('session-id');
const sourceCountEl = document.getElementById('source-count');
const sourcesEl = document.getElementById('sources');
const debugTraceEl = document.getElementById('debug-trace');
const headerStatusEl = document.getElementById('header-status');
const exampleBtn = document.getElementById('example-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const quickChips = document.querySelectorAll('.quick-chip');

const API_BASE = 'http://localhost:8101';
let sessionId = null;

const EXAMPLE_PROMPT = 'I have tomatoes in Bekaa at flowering stage, and the leaves show yellow spots. What might be causing this, how much water do I need this week for 800 square meters, and what fertilizer should I consider?';

exampleBtn.addEventListener('click', () => {
  messageEl.value = EXAMPLE_PROMPT;
  messageEl.focus();
});

newChatBtn.addEventListener('click', () => resetChat());

quickChips.forEach((chip) => {
  chip.addEventListener('click', () => {
    messageEl.value = chip.dataset.prompt || '';
    messageEl.focus();
  });
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = messageEl.value.trim();
  if (!message) return;

  appendMessage({ role: 'user', label: 'You', text: message });
  messageEl.value = '';
  headerStatusEl.textContent = 'Thinking';
  statusEl.textContent = 'Sending request to Agent System A...';
  const loadingId = appendLoadingMessage();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const data = await res.json();
    removeMessage(loadingId);

    if (!res.ok) {
      throw new Error(data.detail || 'Request failed.');
    }

    sessionId = data.session_id;
    sessionIdEl.textContent = truncateMiddle(sessionId, 24);
    headerStatusEl.textContent = 'Responded';
    statusEl.textContent = `Completed with route: ${(data.route || []).join(' → ') || 'default'}`;

    appendMessage({
      role: 'assistant',
      label: 'Farm Copilot',
      subtitle: 'Grounded answer',
      html: renderAnswer(data.answer, data.disclaimer),
    });

    renderRoutes(data.route || []);
    renderSources(data.sources || []);
    renderDebugTrace(data.debug_trace || []);
  } catch (error) {
    removeMessage(loadingId);
    headerStatusEl.textContent = 'Error';
    statusEl.textContent = `Error: ${error.message}`;
    appendMessage({
      role: 'assistant',
      label: 'System',
      subtitle: 'Request failed',
      text: `The request failed. ${error.message}. Check whether Agent A is reachable and review its logs if needed.`,
      error: true,
    });
  }
});

function resetChat() {
  sessionId = null;
  sessionIdEl.textContent = 'Not started';
  statusEl.textContent = 'Ready for a new request.';
  headerStatusEl.textContent = 'Ready';
  routePillsEl.innerHTML = '<span class="pill muted-pill">Multi-agent</span><span class="pill active-pill">Ready</span>';
  routeSummaryEl.innerHTML = '<span class="pill muted-pill">Waiting</span>';
  sourceCountEl.textContent = '0';
  sourcesEl.className = 'source-list empty-state';
  sourcesEl.textContent = 'Retrieved source snippets will appear here.';
  debugTraceEl.textContent = 'No trace yet.';
  messagesEl.innerHTML = `
    <article class="message assistant intro-message">
      <div class="message-avatar assistant-avatar">AI</div>
      <div class="message-body assistant-body">
        <div class="message-header">
          <span class="sender-name">Farm Copilot</span>
          <span class="sender-role">LangGraph supervisor + specialists</span>
        </div>
        <div class="rendered-answer">
          <p>Describe the crop, region, growth stage, area, symptoms, or soil context. The system can route across pest reasoning, irrigation planning, and soil or fertilizer support.</p>
        </div>
      </div>
    </article>
  `;
  messageEl.focus();
}

function appendMessage({ role, label, subtitle = '', text = '', html = '', error = false }) {
  const article = document.createElement('article');
  article.className = `message ${role}`;
  article.dataset.messageId = crypto.randomUUID();

  const avatar = document.createElement('div');
  avatar.className = `message-avatar ${role === 'assistant' ? 'assistant-avatar' : 'user-avatar'}`;
  avatar.textContent = role === 'assistant' ? 'AI' : 'You';

  const body = document.createElement('div');
  body.className = `message-body ${role === 'assistant' ? 'assistant-body' : 'user-body'}`;
  if (error) {
    body.style.borderColor = '#f1caca';
    body.style.background = '#fff8f8';
  }

  const header = document.createElement('div');
  header.className = 'message-header';
  header.innerHTML = `
    <span class="sender-name">${escapeHtml(label)}</span>
    <span class="sender-role">${escapeHtml(subtitle || (role === 'assistant' ? 'Grounded answer' : 'Prompt'))}</span>
  `;

  const content = document.createElement('div');
  content.className = 'rendered-answer';
  content.innerHTML = html || `<p>${escapeHtml(text)}</p>`;

  body.appendChild(header);
  body.appendChild(content);
  article.appendChild(avatar);
  article.appendChild(body);
  messagesEl.appendChild(article);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return article.dataset.messageId;
}

function appendLoadingMessage() {
  const id = crypto.randomUUID();
  const article = document.createElement('article');
  article.className = 'message assistant';
  article.dataset.messageId = id;
  article.innerHTML = `
    <div class="message-avatar assistant-avatar">AI</div>
    <div class="message-body assistant-body">
      <div class="message-header">
        <span class="sender-name">Farm Copilot</span>
        <span class="sender-role">Coordinating specialists</span>
      </div>
      <div class="rendered-answer"><p class="loading-dots">Thinking</p></div>
    </div>
  `;
  messagesEl.appendChild(article);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return id;
}

function removeMessage(id) {
  if (!id) return;
  const node = messagesEl.querySelector(`[data-message-id="${id}"]`);
  if (node) node.remove();
}

function renderRoutes(routes) {
  const normalized = Array.isArray(routes) ? routes : [];
  routePillsEl.innerHTML = ['Multi-agent', ...normalized.map(capitalize)]
    .map((route, index) => `<span class="pill ${index === 0 ? 'muted-pill' : 'active-pill'}">${escapeHtml(route)}</span>`)
    .join('');

  routeSummaryEl.innerHTML = normalized.length
    ? normalized.map((route) => `<span class="pill">${escapeHtml(capitalize(route))}</span>`).join('')
    : '<span class="pill muted-pill">No route reported</span>';
}

function renderSources(sources) {
  if (!Array.isArray(sources) || !sources.length) {
    sourceCountEl.textContent = '0';
    sourcesEl.className = 'source-list empty-state';
    sourcesEl.textContent = 'No source snippets returned for this message.';
    return;
  }

  sourceCountEl.textContent = String(sources.length);
  sourcesEl.className = 'source-list';
  sourcesEl.innerHTML = sources.slice(0, 6).map((item) => {
    const title = item.title && item.title !== 'Untitled' ? item.title : 'Retrieved source';
    const path = item.source_path && item.source_path !== 'unknown' ? item.source_path : 'Local corpus';
    const score = Number(item.score || 0).toFixed(3);
    const snippet = shorten(item.text || '', 220);
    return `
      <article class="source-card">
        <span class="source-title">${escapeHtml(title)}</span>
        <div class="source-meta">${escapeHtml(path)} · score ${score}</div>
        <div class="source-text">${escapeHtml(snippet)}</div>
      </article>
    `;
  }).join('');
}

function renderDebugTrace(trace) {
  if (Array.isArray(trace)) {
    debugTraceEl.textContent = trace.join('\n');
    return;
  }
  if (typeof trace === 'string' && trace.trim()) {
    debugTraceEl.textContent = trace;
    return;
  }
  debugTraceEl.textContent = 'No trace yet.';
}

function renderAnswer(answer = '', disclaimer = '') {
  const safeText = normalizeAnswer(answer || '');
  const lines = safeText.split('\n').map((line) => line.trim()).filter(Boolean);
  const html = [];
  let listOpen = false;

  const closeList = () => {
    if (listOpen) {
      html.push('</ul>');
      listOpen = false;
    }
  };

  lines.forEach((line) => {
    if (/^###\s+/.test(line) || /^##\s+/.test(line)) {
      closeList();
      html.push(`<h4>${escapeHtml(line.replace(/^#+\s*/, ''))}</h4>`);
      return;
    }

    if (/^-\s+/.test(line)) {
      if (!listOpen) {
        html.push('<ul>');
        listOpen = true;
      }
      html.push(`<li>${escapeHtml(line.replace(/^-\s+/, ''))}</li>`);
      return;
    }

    closeList();
    html.push(`<p>${formatInline(line)}</p>`);
  });

  closeList();

  if (disclaimer) {
    html.push(`<p><strong>Disclaimer:</strong> ${escapeHtml(disclaimer)}</p>`);
  }

  return html.join('');
}

function normalizeAnswer(text) {
  return String(text).replace(/mÂ²/g, 'm²').replace(/\r/g, '').trim();
}

function formatInline(text) {
  const escaped = escapeHtml(text);
  return escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function truncateMiddle(text, maxLength) {
  if (!text || text.length <= maxLength) return text || '';
  const part = Math.floor((maxLength - 3) / 2);
  return `${text.slice(0, part)}...${text.slice(-part)}`;
}

function shorten(text, maxLength) {
  const value = String(text || '').replace(/\s+/g, ' ').trim();
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}…`;
}

function capitalize(value) {
  return String(value || '').charAt(0).toUpperCase() + String(value || '').slice(1);
}

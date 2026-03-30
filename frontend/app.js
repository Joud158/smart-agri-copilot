const STORAGE_KEY = 'smart_agri_frontend_v6';
const PANEL_KEY = 'smart_agri_panel_state_v6';

function resolveApiBase() {
  const queryParam = new URLSearchParams(window.location.search).get('api');
  if (queryParam) return queryParam.replace(/\/$/, '');

  const configured = window.__SMART_AGRI_CONFIG__?.apiBase;
  if (configured) return configured.replace(/\/$/, '');

  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8101';
  }
  return `${window.location.protocol}//${window.location.hostname}:8101`;
}

const API_BASE = resolveApiBase();

const els = {
  historyPanel: document.getElementById('historyPanel'),
  sourcesPanel: document.getElementById('sourcesPanel'),
  openLeftBtn: document.getElementById('openLeftBtn'),
  openRightBtn: document.getElementById('openRightBtn'),
  closeLeftBtn: document.getElementById('closeLeftBtn'),
  closeRightBtn: document.getElementById('closeRightBtn'),
  statusPill: document.getElementById('statusPill'),
  historyList: document.getElementById('historyList'),
  historySearch: document.getElementById('historySearch'),
  newChatBtn: document.getElementById('newChatBtn'),
  messages: document.getElementById('messages'),
  input: document.getElementById('messageInput'),
  sendBtn: document.getElementById('sendBtn'),
  micBtn: document.getElementById('micBtn'),
  composerHint: document.getElementById('composerHint'),
  sourcesList: document.getElementById('sourcesList'),
  sessionId: document.getElementById('sessionId'),
  routeText: document.getElementById('routeText'),
  traceList: document.getElementById('traceList'),
  copyTraceBtn: document.getElementById('copyTraceBtn'),
  previewBanner: document.getElementById('previewBanner'),
  clearPreviewBtn: document.getElementById('clearPreviewBtn'),
};

const state = {
  activeId: null,
  conversations: [],
  recognition: null,
  isStreaming: false,
  panels: { left: true, right: true },
};

function uid() {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
}

function compactText(text = '') {
  return String(text).replace(/mÂ²/g, 'm²').replace(/\s+/g, ' ').trim();
}

function normalizeAnswerText(text = '') {
  return String(text)
    .replace(/\r/g, '')
    .replace(/mÂ²/g, 'm²')
    .replace(/\u00A0/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\s+###\s+/g, '\n\n### ')
    .replace(/\s+##\s+/g, '\n\n## ')
    .replace(/\s+-\s+/g, '\n- ')
    .trim();
}

function escapeHtml(text = '') {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function setStatus(text) {
  els.statusPill.textContent = text;
}

function saveConversations() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ conversations: state.conversations, activeId: state.activeId }));
}

function savePanels() {
  localStorage.setItem(PANEL_KEY, JSON.stringify(state.panels));
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    state.conversations = Array.isArray(saved.conversations) ? saved.conversations : [];
    state.activeId = saved.activeId || null;
  } catch {
    state.conversations = [];
    state.activeId = null;
  }

  try {
    const savedPanels = JSON.parse(localStorage.getItem(PANEL_KEY) || '{}');
    if (typeof savedPanels.left === 'boolean') state.panels.left = savedPanels.left;
    if (typeof savedPanels.right === 'boolean') state.panels.right = savedPanels.right;
  } catch {}
}

function applyPanelState() {
  document.body.classList.toggle('left-open', state.panels.left);
  document.body.classList.toggle('left-closed', !state.panels.left);
  document.body.classList.toggle('right-open', state.panels.right);
  document.body.classList.toggle('right-closed', !state.panels.right);
}

function ensureActiveConversation() {
  if (state.activeId && state.conversations.some(item => item.id === state.activeId)) return;
  const conversation = {
    id: uid(),
    title: 'New chat',
    createdAt: new Date().toLocaleString(),
    sessionId: null,
    route: [],
    trace: [],
    sources: [],
    messages: [],
  };
  state.conversations.unshift(conversation);
  state.activeId = conversation.id;
  saveConversations();
}

function getActiveConversation() {
  ensureActiveConversation();
  return state.conversations.find(item => item.id === state.activeId);
}

function getHistoryFilter() {
  return (els.historySearch.value || '').trim().toLowerCase();
}

function setInputValue(value, hint = '') {
  els.input.value = value;
  els.previewBanner.classList.toggle('hidden', !value);
  els.composerHint.textContent = hint || 'Edit the loaded example if needed, then press send.';
  autoResize();
  els.input.focus();
}

function clearLoadedExample() {
  els.previewBanner.classList.add('hidden');
  els.composerHint.textContent = 'Choose an example to preview it before sending, or type your own question.';
}

function autoResize() {
  els.input.style.height = 'auto';
  els.input.style.height = `${Math.min(els.input.scrollHeight, 180)}px`;
}

function stripMarkdown(text = '') {
  return String(text)
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^[-•]\s*/gm, '')
    .trim();
}

function inlineFormat(text = '') {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function markdownishToHtml(text = '') {
  const source = normalizeAnswerText(text);
  if (!source) return '<p>No answer returned.</p>';

  const lines = source.split('\n');
  const chunks = [];
  let listItems = [];
  let paragraph = [];

  const flushList = () => {
    if (!listItems.length) return;
    chunks.push(`<ul>${listItems.map(item => `<li>${inlineFormat(item)}</li>`).join('')}</ul>`);
    listItems = [];
  };

  const flushParagraph = () => {
    if (!paragraph.length) return;
    chunks.push(`<p>${inlineFormat(paragraph.join(' '))}</p>`);
    paragraph = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      flushParagraph();
      continue;
    }

    if (/^###\s+/.test(line)) {
      flushList();
      flushParagraph();
      chunks.push(`<h3>${inlineFormat(line.replace(/^###\s+/, ''))}</h3>`);
      continue;
    }
    if (/^##\s+/.test(line)) {
      flushList();
      flushParagraph();
      chunks.push(`<h4>${inlineFormat(line.replace(/^##\s+/, ''))}</h4>`);
      continue;
    }
    if (/^[-•]\s+/.test(line)) {
      flushParagraph();
      listItems.push(line.replace(/^[-•]\s+/, ''));
      continue;
    }

    paragraph.push(line.replace(/^#+\s*/, ''));
  }

  flushList();
  flushParagraph();
  return chunks.join('');
}

function renderHistory() {
  const filter = getHistoryFilter();
  const items = state.conversations.filter(item => {
    if (!filter) return true;
    const messagesText = (item.messages || []).map(msg => msg.text || '').join(' ').toLowerCase();
    return (item.title || '').toLowerCase().includes(filter) || messagesText.includes(filter);
  });

  if (!items.length) {
    els.historyList.innerHTML = '<div class="empty-state-small">No conversations match that search.</div>';
    return;
  }

  els.historyList.innerHTML = items.map(item => {
    const last = item.messages?.[item.messages.length - 1]?.text || '';
    const preview = compactText(last).slice(0, 64);
    return `
      <button class="history-item ${item.id === state.activeId ? 'active' : ''}" data-id="${item.id}">
        <div class="history-item-title">${escapeHtml(item.title || 'New chat')}</div>
        <div class="history-item-sub">${escapeHtml(preview || item.createdAt || '')}</div>
      </button>
    `;
  }).join('');

  els.historyList.querySelectorAll('.history-item').forEach(button => {
    button.addEventListener('click', () => {
      state.activeId = button.dataset.id;
      saveConversations();
      renderAll();
    });
  });
}

function renderMessages() {
  const conversation = getActiveConversation();
  const messages = conversation.messages || [];

  if (!messages.length) {
    els.messages.innerHTML = `
      <article class="message assistant">
        <div class="avatar assistant-avatar">AI</div>
        <div class="bubble-card">
          <div class="message-head"><strong>Assistant</strong></div>
          <div class="message-body">
            <p>Ask about crops, symptoms, irrigation, soil interpretation, or fertilizer guidance. The interface now streams responses as they are generated.</p>
          </div>
        </div>
      </article>
    `;
    return;
  }

  els.messages.innerHTML = '';
  messages.forEach(message => {
    const template = document.getElementById(message.role === 'assistant' ? 'assistantMessageTemplate' : 'userMessageTemplate');
    const node = template.content.firstElementChild.cloneNode(true);
    const body = node.querySelector('.message-body');

    body.innerHTML = message.role === 'assistant'
      ? markdownishToHtml(message.text || (message.pending ? 'Thinking…' : 'No answer returned.'))
      : `<p>${escapeHtml(compactText(message.text))}</p>`;

    if (message.role === 'assistant') {
      const speakButton = node.querySelector('.speak-answer');
      if ('speechSynthesis' in window) {
        speakButton.classList.remove('hidden');
        speakButton.addEventListener('click', () => speakText(stripMarkdown(message.text || '')));
      }
    }

    els.messages.appendChild(node);
  });
  els.messages.scrollTop = els.messages.scrollHeight;
}

function deriveSourceTitle(source) {
  const explicit = compactText(source?.title || '');
  if (explicit && !/^untitled$/i.test(explicit) && !/^source$/i.test(explicit)) return explicit;
  const text = String(source?.text || '');
  const headingMatch = text.match(/^#{1,6}\s*(.+)$/m);
  if (headingMatch) return compactText(headingMatch[1]);
  const firstSentence = compactText(stripMarkdown(text).split(/[.!?]/)[0] || 'Supporting source');
  return firstSentence.slice(0, 80) || 'Supporting source';
}

function summarizeSource(source) {
  const title = deriveSourceTitle(source);
  const cleaned = compactText(stripMarkdown(source?.text || ''));
  const snippet = cleaned.startsWith(title) ? cleaned.slice(title.length).trim() : cleaned;
  return {
    title,
    snippet: (snippet || cleaned || 'Relevant supporting information used for this answer.').slice(0, 220),
  };
}

function renderSources() {
  const conversation = getActiveConversation();
  const sources = Array.isArray(conversation.sources) ? conversation.sources : [];

  if (!sources.length) {
    els.sourcesList.innerHTML = '<div class="empty-state-small">No sources yet.</div>';
  } else {
    els.sourcesList.innerHTML = sources.map(source => {
      const summary = summarizeSource(source);
      const metadata = source.metadata || {};
      const badges = [metadata.topic, metadata.crop_name, metadata.growth_stage].filter(Boolean);
      const score = typeof source.score === 'number' ? source.score.toFixed(3) : '—';
      return `
        <article class="source-card">
          <div class="source-title">${escapeHtml(summary.title)}</div>
          <div class="source-text">${escapeHtml(summary.snippet)}</div>
          <div class="source-text" style="margin-top:10px;font-size:0.78rem;color:#6b7d7c;">
            <strong>File:</strong> ${escapeHtml(source.source_path || 'unknown')} &nbsp;•&nbsp; <strong>Score:</strong> ${escapeHtml(score)}
          </div>
          ${badges.length ? `<div class="source-text" style="margin-top:8px;font-size:0.78rem;color:#587271;">${badges.map(badge => `<span style="display:inline-block;margin-right:6px;padding:3px 8px;border-radius:999px;background:#eef6f5;">${escapeHtml(String(badge))}</span>`).join('')}</div>` : ''}
        </article>
      `;
    }).join('');
  }

  els.sessionId.textContent = conversation.sessionId || '—';
  els.routeText.textContent = (conversation.route || []).length ? conversation.route.join(', ') : '—';
  const trace = Array.isArray(conversation.trace) ? conversation.trace : [];
  els.traceList.innerHTML = trace.length
    ? trace.map(item => `<div class="trace-chip">${escapeHtml(compactText(String(item)))}</div>`).join('')
    : '<div class="empty-state-small">No trace available.</div>';
}

function renderAll() {
  renderHistory();
  renderMessages();
  renderSources();
  applyPanelState();
}

function detectSpeechLanguage(text = '') {
  if (/[\u0600-\u06FF]/.test(text)) return 'ar-LB';
  if (/[éèêëàâîïôöùûüç]/i.test(text)) return 'fr-FR';
  return navigator.language || 'en-US';
}

function speakText(text) {
  if (!('speechSynthesis' in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(compactText(text));
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.lang = detectSpeechLanguage(text);
  window.speechSynthesis.speak(utterance);
}

function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    els.micBtn.classList.add('hidden');
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = (navigator.languages && navigator.languages[0]) || navigator.language || 'en-US';
  recognition.interimResults = true;
  recognition.continuous = false;
  state.recognition = recognition;

  let finalText = '';
  recognition.onstart = () => {
    finalText = '';
    els.micBtn.classList.add('active');
    els.composerHint.textContent = `Listening in ${recognition.lang}… speak clearly and pause when you finish.`;
  };

  recognition.onresult = (event) => {
    let interim = '';
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const transcript = event.results[index][0].transcript;
      if (event.results[index].isFinal) finalText += `${transcript} `;
      else interim += transcript;
    }
    els.input.value = `${finalText}${interim}`.trim();
    autoResize();
  };

  recognition.onend = () => {
    els.micBtn.classList.remove('active');
    els.composerHint.textContent = 'Review the transcribed text, then press send.';
  };

  recognition.onerror = () => {
    els.micBtn.classList.remove('active');
    els.composerHint.textContent = 'Microphone access failed or was denied.';
  };

  els.micBtn.addEventListener('click', () => {
    recognition.lang = detectSpeechLanguage(els.input.value || navigator.language || 'en-US');
    if (els.micBtn.classList.contains('active')) recognition.stop();
    else recognition.start();
  });
}

async function consumeSSE(response, handlers) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf('\n\n');

      const lines = rawEvent.split('\n');
      let eventName = 'message';
      const dataLines = [];
      for (const line of lines) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim();
        if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;

      let payload = dataLines.join('\n');
      try {
        payload = JSON.parse(payload);
      } catch {}

      if (handlers[eventName]) handlers[eventName](payload);
    }
  }
}

async function sendMessage(prefill = null) {
  const text = compactText(prefill ?? els.input.value);
  if (!text || state.isStreaming) return;

  ensureActiveConversation();
  const conversation = getActiveConversation();
  conversation.messages.push({ role: 'user', text });
  conversation.title = conversation.title === 'New chat' ? `${text.slice(0, 44)}${text.length > 44 ? '…' : ''}` : conversation.title;
  const assistantMessage = { role: 'assistant', text: 'Thinking…', pending: true };
  conversation.messages.push(assistantMessage);
  conversation.sources = [];
  conversation.trace = [];
  clearLoadedExample();
  saveConversations();
  renderAll();

  els.input.value = '';
  autoResize();
  setStatus('Streaming…');
  els.sendBtn.disabled = true;
  state.isStreaming = true;

  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: conversation.sessionId, stream: true }),
    });
    if (!response.ok || !response.body) throw new Error(`Request failed with status ${response.status}`);

    let accumulated = '';
    await consumeSSE(response, {
      meta(payload) {
        conversation.sessionId = payload.session_id || conversation.sessionId;
        conversation.route = Array.isArray(payload.route) ? payload.route : conversation.route;
        saveConversations();
        renderSources();
      },
      token(payload) {
        accumulated += payload.text || '';
        assistantMessage.text = normalizeAnswerText(accumulated || 'Thinking…');
        assistantMessage.pending = true;
        renderMessages();
      },
      done(payload) {
        assistantMessage.text = normalizeAnswerText(payload.answer || accumulated || 'No answer returned.');
        assistantMessage.pending = false;
        conversation.sessionId = payload.session_id || conversation.sessionId;
        conversation.route = Array.isArray(payload.route) ? payload.route : [];
        conversation.trace = Array.isArray(payload.debug_trace) ? payload.debug_trace : [];
        conversation.sources = Array.isArray(payload.sources) ? payload.sources : [];
        saveConversations();
        renderAll();
      },
    });

    setStatus('Ready');
  } catch (error) {
    assistantMessage.text = `I could not complete the request. ${error.message}`;
    assistantMessage.pending = false;
    saveConversations();
    renderAll();
    setStatus('Error');
  } finally {
    els.sendBtn.disabled = false;
    state.isStreaming = false;
  }
}

function startNewChat() {
  state.activeId = null;
  ensureActiveConversation();
  clearLoadedExample();
  renderAll();
  els.input.value = '';
  autoResize();
  els.input.focus();
}

function checkHealth() {
  fetch(`${API_BASE}/health`)
    .then(response => setStatus(response.ok ? 'Ready' : 'Backend offline'))
    .catch(() => setStatus('Backend offline'));
}

function setupEvents() {
  els.newChatBtn.addEventListener('click', startNewChat);
  els.historySearch.addEventListener('input', renderHistory);
  els.sendBtn.addEventListener('click', () => sendMessage());
  els.input.addEventListener('input', autoResize);
  els.input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  document.querySelectorAll('.example-chip').forEach(button => {
    button.addEventListener('click', () => {
      setInputValue(button.dataset.prompt || '', 'Example loaded. You can edit it before sending.');
    });
  });

  els.clearPreviewBtn.addEventListener('click', () => {
    els.input.value = '';
    clearLoadedExample();
    autoResize();
  });

  els.closeLeftBtn.addEventListener('click', () => {
    state.panels.left = false;
    savePanels();
    applyPanelState();
  });
  els.openLeftBtn.addEventListener('click', () => {
    state.panels.left = true;
    savePanels();
    applyPanelState();
  });
  els.closeRightBtn.addEventListener('click', () => {
    state.panels.right = false;
    savePanels();
    applyPanelState();
  });
  els.openRightBtn.addEventListener('click', () => {
    state.panels.right = true;
    savePanels();
    applyPanelState();
  });

  els.copyTraceBtn.addEventListener('click', async () => {
    const conversation = getActiveConversation();
    try {
      await navigator.clipboard.writeText((conversation.trace || []).join('\n'));
      els.copyTraceBtn.textContent = 'Copied';
      setTimeout(() => { els.copyTraceBtn.textContent = 'Copy'; }, 900);
    } catch {}
  });
}

loadState();
setupEvents();
setupSpeechRecognition();
ensureActiveConversation();
renderAll();
autoResize();
checkHealth();

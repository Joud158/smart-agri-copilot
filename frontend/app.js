const API_BASE = 'http://localhost:8101';
const STORAGE_KEY = 'smart_agri_frontend_v5';
const PANEL_KEY = 'smart_agri_panel_state_v5';

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
  latestAnswer: '',
  loadedExample: '',
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
  if (state.activeId && state.conversations.some(c => c.id === state.activeId)) return;
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
  return state.conversations.find(c => c.id === state.activeId);
}

function setInputValue(value, hint = '') {
  els.input.value = value;
  state.loadedExample = value;
  els.previewBanner.classList.toggle('hidden', !value);
  els.composerHint.textContent = hint || 'Edit the loaded example if needed, then press send.';
  autoResize();
  els.input.focus();
}

function clearLoadedExample() {
  state.loadedExample = '';
  els.previewBanner.classList.add('hidden');
  els.composerHint.textContent = 'Choose an example to preview it before sending, or type your own question.';
}

function getHistoryFilter() {
  return (els.historySearch.value || '').trim().toLowerCase();
}

function escapeHtml(text = '') {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderHistory() {
  const filter = getHistoryFilter();
  const items = state.conversations.filter(c => {
    if (!filter) return true;
    const messagesText = (c.messages || []).map(m => m.text || '').join(' ').toLowerCase();
    return (c.title || '').toLowerCase().includes(filter) || messagesText.includes(filter);
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

  els.historyList.querySelectorAll('.history-item').forEach(btn => {
    btn.addEventListener('click', () => {
      state.activeId = btn.dataset.id;
      saveConversations();
      renderAll();
    });
  });
}

function stripMarkdown(text = '') {
  return String(text)
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^[-•]\s*/gm, '')
    .trim();
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
            <p>Ask about crops, symptoms, irrigation, soil interpretation, or fertilizer guidance. Choose an example to preview it before sending, or type your own question below.</p>
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
      ? markdownishToHtml(message.text)
      : `<p>${escapeHtml(compactText(message.text))}</p>`;

    if (message.role === 'assistant') {
      const speakButton = node.querySelector('.speak-answer');
      if ('speechSynthesis' in window) {
        speakButton.classList.remove('hidden');
        speakButton.addEventListener('click', () => speakText(stripMarkdown(message.text)));
      }
    }

    els.messages.appendChild(node);
  });

  els.messages.scrollTop = els.messages.scrollHeight;
}

function renderSources() {
  const conversation = getActiveConversation();
  const sources = Array.isArray(conversation.sources) ? conversation.sources : [];
  const useful = sources.slice(0, 4).map(summarizeSource);

  if (!useful.length) {
    els.sourcesList.innerHTML = '<div class="empty-state-small">Useful source snippets will appear here after the assistant answers.</div>';
  } else {
    els.sourcesList.innerHTML = useful.map(source => `
      <article class="source-card">
        <div class="source-title">${escapeHtml(source.title)}</div>
        <div class="source-text">${escapeHtml(source.snippet)}</div>
      </article>
    `).join('');
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

function autoResize() {
  els.input.style.height = 'auto';
  els.input.style.height = `${Math.min(els.input.scrollHeight, 180)}px`;
}

async function sendMessage(prefill = null) {
  const text = compactText(prefill ?? els.input.value);
  if (!text) return;

  ensureActiveConversation();
  const conversation = getActiveConversation();
  conversation.messages.push({ role: 'user', text });
  conversation.title = conversation.title === 'New chat' ? `${text.slice(0, 44)}${text.length > 44 ? '…' : ''}` : conversation.title;
  clearLoadedExample();
  saveConversations();
  renderAll();
  els.input.value = '';
  autoResize();

  setStatus('Thinking…');
  els.sendBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: conversation.sessionId }),
    });

    if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
    const data = await response.json();

    conversation.sessionId = data.session_id || conversation.sessionId;
    conversation.route = Array.isArray(data.route) ? data.route : [];
    conversation.trace = Array.isArray(data.debug_trace) ? data.debug_trace : [];
    conversation.sources = Array.isArray(data.sources) ? data.sources : [];
    conversation.messages.push({ role: 'assistant', text: normalizeAnswerText(data.answer || 'No answer returned.') });
    state.latestAnswer = normalizeAnswerText(data.answer || '');

    saveConversations();
    renderAll();
    setStatus('Ready');
  } catch (error) {
    conversation.messages.push({ role: 'assistant', text: `I could not complete the request. ${error.message}` });
    saveConversations();
    renderAll();
    setStatus('Error');
  } finally {
    els.sendBtn.disabled = false;
  }
}

function startNewChat() {
  state.activeId = null;
  ensureActiveConversation();
  clearLoadedExample();
  state.latestAnswer = '';
  renderAll();
  els.input.value = '';
  autoResize();
  els.input.focus();
}

function speakText(text) {
  if (!('speechSynthesis' in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(compactText(text));
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.lang = 'en-US';
  window.speechSynthesis.speak(utterance);
}

function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    els.micBtn.classList.add('hidden');
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = true;
  recognition.continuous = false;
  state.recognition = recognition;

  let finalText = '';
  recognition.onstart = () => {
    finalText = '';
    els.micBtn.classList.add('active');
    els.composerHint.textContent = 'Listening… speak clearly and pause when you finish.';
  };

  recognition.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalText += `${transcript} `;
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
    if (els.micBtn.classList.contains('active')) recognition.stop();
    else recognition.start();
  });
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

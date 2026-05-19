/* =============================================================
   app.js  —  AI Interview Agent  |  Frontend Controller
   =============================================================
   Sections:
     CONFIG        ─ API URL
     STATE         ─ single source of truth object
     INIT          ─ startup
     UPLOAD        ─ file handling + start interview
     INTERVIEW     ─ Q&A flow, chat rendering
     REPORT        ─ score ring, accordion, feedback display
     HISTORY       ─ fetch & render DB records
     UI HELPERS    ─ screen switching, modals, error display
   ============================================================= */


/* ─── CONFIG ─────────────────────────────────────────────────
   Change port here if your Flask server runs somewhere else.  */
const API = 'http://localhost:5000/api';


/* ─── STATE ──────────────────────────────────────────────────
   All mutable data lives here.  Never store critical state in
   the DOM — the DOM is just a view of this object.            */
const S = {
  sessionId      : null,    // DB row id returned by /start-interview
  candidateName  : '',
  skills         : [],      // Extracted skills from resume
  questions      : [],      // [{question, type, topic}, ...]
  currentQ       : 0,       // Index of question currently being asked
  qaResults      : [],      // [{question, answer, score, feedback, ...}]
  selectedFile   : null,    // File object from input
  busy           : false,   // True while an API call is in flight
};


/* ─── INIT ───────────────────────────────────────────────────*/
document.addEventListener('DOMContentLoaded', () => {
  showScreen('upload');
});


/* =============================================================
   UPLOAD SCREEN
   ============================================================= */

/** Called when user picks a file via the file picker dialog. */
function onFileSelect(event) {
  const file = event.target.files[0];
  if (file) setFile(file);
}

/** Allow drop events on the drop zone. */
function onDragOver(event) {
  event.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}

function onDragLeave() {
  document.getElementById('drop-zone').classList.remove('drag-over');
}

/** Handle a file being dropped onto the drop zone. */
function onDrop(event) {
  event.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  const file = event.dataTransfer.files[0];
  if (file) setFile(file);
}

/**
 * Validates the file, stores it in state, and updates the UI.
 * @param {File} file
 */
function setFile(file) {
  const ALLOWED = ['pdf', 'docx', 'txt'];
  const ext     = file.name.split('.').pop().toLowerCase();

  if (!ALLOWED.includes(ext)) {
    showUploadError('Only PDF, DOCX, and TXT files are accepted.');
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showUploadError('File must be under 5 MB.');
    return;
  }

  S.selectedFile = file;
  clearUploadError();

  // Show the filename badge
  document.getElementById('drop-zone').classList.add('hidden');
  document.getElementById('file-badge-name').textContent = file.name;
  document.getElementById('file-badge').classList.remove('hidden');

  // Enable the Start button
  document.getElementById('start-btn').disabled = false;
}

/** Removes the chosen file and resets upload UI. */
function clearFile() {
  S.selectedFile = null;
  document.getElementById('file-badge').classList.add('hidden');
  document.getElementById('drop-zone').classList.remove('hidden');
  document.getElementById('file-input').value = '';
  document.getElementById('start-btn').disabled = true;
}

/**
 * Triggered by the "Begin Interview" button.
 * POSTs the resume to /api/start-interview, then starts the Q&A.
 */
async function startInterview() {
  if (!S.selectedFile || S.busy) return;

  const name = document.getElementById('candidate-name').value.trim() || 'Candidate';
  S.candidateName = name;

  // Build multipart form data
  const fd = new FormData();
  fd.append('resume', S.selectedFile);
  fd.append('candidate_name', name);

  // Show loading spinner, disable button
  setUploadLoading(true);
  clearUploadError();

  try {
    const res  = await fetch(`${API}/start-interview`, { method: 'POST', body: fd });
    const data = await res.json();

    if (!res.ok || data.error) throw new Error(data.error || 'Server error.');

    // Store returned data
    S.sessionId = data.session_id;
    S.skills    = data.skills    || [];
    S.questions = data.questions || [];
    S.qaResults = [];
    S.currentQ  = 0;

    // Switch to interview screen and begin
    showScreen('interview');
    initInterviewScreen();

  } catch (err) {
    showUploadError(err.message);
  } finally {
    setUploadLoading(false);
  }
}

/* Upload UI helpers */
function setUploadLoading(on) {
  S.busy = on;
  document.getElementById('upload-loading').classList.toggle('hidden', !on);
  document.getElementById('start-btn').disabled = on;
}
function showUploadError(msg) {
  const el = document.getElementById('upload-error');
  el.textContent = msg;
  el.classList.remove('hidden');
}
function clearUploadError() {
  document.getElementById('upload-error').classList.add('hidden');
}


/* =============================================================
   INTERVIEW SCREEN
   ============================================================= */

/** Sets up the interview screen and asks the first question. */
function initInterviewScreen() {
  // Put candidate's name in topbar
  document.getElementById('ibar-name').textContent = S.candidateName;

  // Render skills chips
  const chipsEl = document.getElementById('skills-chips');
  chipsEl.innerHTML = '';
  S.skills.forEach(skill => {
    const chip = document.createElement('span');
    chip.className = 'skill-chip';
    chip.textContent = skill;
    chipsEl.appendChild(chip);
  });

  // Clear old messages
  document.getElementById('chat-messages').innerHTML = '';

  // Update progress
  updateProgress();

  // Greeting from AI
  addAiMessage(`👋 Hello <strong>${S.candidateName}</strong>! I'm your AI interviewer today.
    I've analysed your resume and prepared <strong>${S.questions.length} personalized questions</strong>.
    Take your time — there's no rush.`);

  // Ask first question after a short pause
  setTimeout(askCurrentQuestion, 900);
}

/** Adds the current question to the chat. */
function askCurrentQuestion() {
  if (S.currentQ >= S.questions.length) {
    finishInterview();
    return;
  }

  const q   = S.questions[S.currentQ];
  const num = S.currentQ + 1;

  showTyping(() => {
    addAiMessage(
      `<span style="font-size:11px;font-weight:700;letter-spacing:.8px;
        text-transform:uppercase;color:var(--c-muted);display:block;margin-bottom:6px;">
        ${q.type.toUpperCase()} · ${q.topic}
      </span>
      <strong>Q${num}:</strong> ${q.question}`
    );
    document.getElementById('answer-input').focus();
  }, 700);
}

/**
 * Called when user clicks Submit (or presses Ctrl+Enter).
 * Sends the answer to /api/evaluate, shows result, then moves on.
 */
async function submitAnswer() {
  if (S.busy) return;

  const textarea = document.getElementById('answer-input');
  const answer   = textarea.value.trim();

  // Validation
  if (!answer) { textarea.focus(); return; }
  if (answer.length < 8) {
    textarea.style.borderColor = 'var(--c-red)';
    setTimeout(() => textarea.style.borderColor = '', 1500);
    return;
  }

  S.busy = true;
  document.getElementById('submit-btn').disabled = true;

  const question = S.questions[S.currentQ].question;

  // Show user's answer bubble
  addUserMessage(answer);

  // Clear textarea
  textarea.value = '';
  onCharCount();

  // Show typing indicator while evaluating
  showTyping(null, 300);

  try {
    const res  = await fetch(`${API}/evaluate`, {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify({
        session_id     : S.sessionId,
        question,
        answer,
        question_index : S.currentQ
      })
    });
    const data = await res.json();

    if (!res.ok || data.error) throw new Error(data.error || 'Evaluation failed.');

    removeTyping();

    // Show evaluation result
    showEvaluation(data);

    // Store result
    S.qaResults.push({
      question,
      answer,
      score       : data.score,
      feedback    : data.feedback,
      strengths   : data.strengths   || [],
      improvements: data.improvements || []
    });

    S.currentQ++;

    if (S.currentQ < S.questions.length) {
      // More questions remain
      updateProgress();
      setTimeout(askCurrentQuestion, 1600);
    } else {
      // All done
      setTimeout(() => {
        addAiMessage('✅ That was the last question! Generating your final report now…');
        setTimeout(finishInterview, 2000);
      }, 1400);
    }

  } catch (err) {
    removeTyping();
    addAiMessage(`⚠️ ${err.message} — Moving to the next question.`);
    S.qaResults.push({ question, answer, score: 50, feedback: '', strengths: [], improvements: [] });
    S.currentQ++;
    updateProgress();
    setTimeout(askCurrentQuestion, 2000);
  } finally {
    S.busy = false;
    document.getElementById('submit-btn').disabled = false;
  }
}

/** Ctrl+Enter shortcut to submit. */
function onKeyDown(event) {
  if (event.ctrlKey && event.key === 'Enter') {
    event.preventDefault();
    submitAnswer();
  }
}

/** Updates the character count display. */
function onCharCount() {
  const len = document.getElementById('answer-input').value.length;
  document.getElementById('abar-chars').textContent = `${len} / 600`;
}

/** Updates the progress bar and counter in the topbar. */
function updateProgress() {
  const total   = S.questions.length;
  const done    = S.currentQ;
  const pct     = total ? Math.round((done / total) * 100) : 0;

  document.getElementById('ibar-counter').textContent    = `${done + 1} / ${total}`;
  document.getElementById('ibar-progress-fill').style.width = pct + '%';
}

/* ── Chat rendering helpers ─────────────────────────────────*/

function addAiMessage(html) {
  const row   = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `
    <div class="msg-avatar">◈</div>
    <div class="msg-bubble ai">${html}</div>
  `;
  appendToChat(row);
}

function addUserMessage(text) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  row.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-bubble user">${escHtml(text)}</div>
  `;
  appendToChat(row);
}

/**
 * Renders the evaluation result as a special bubble.
 * @param {{score, feedback, strengths, improvements}} ev
 */
function showEvaluation(ev) {
  const score = ev.score || 0;

  // Pick color based on score
  let color;
  if (score >= 75) color = 'var(--c-green)';
  else if (score >= 55) color = 'var(--c-gold)';
  else if (score >= 35) color = 'var(--c-amber)';
  else color = 'var(--c-red)';

  // Strength tags
  const goodTags = (ev.strengths || [])
    .map(s => `<span class="eval-tag tag-good">✓ ${escHtml(s)}</span>`)
    .join('');

  // Improvement tags
  const impTags = (ev.improvements || [])
    .map(s => `<span class="eval-tag tag-improve">↑ ${escHtml(s)}</span>`)
    .join('');

  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `
    <div class="msg-avatar">◈</div>
    <div class="eval-bubble">
      <div class="eval-score-row">
        <span class="eval-score-num" style="color:${color}">${score}</span>
        <div>
          <div class="eval-score-label">Score / 100</div>
        </div>
      </div>
      <p class="eval-feedback">${escHtml(ev.feedback || '')}</p>
      <div class="eval-tags">${goodTags}${impTags}</div>
    </div>
  `;
  appendToChat(row);
}

let _typingEl = null;

function showTyping(callback, delay = 600) {
  const row = document.createElement('div');
  row.className = 'typing-row';
  row.id = '__typing__';
  row.innerHTML = `
    <div class="msg-avatar">◈</div>
    <div class="typing-bubble">
      <div class="t-dot"></div>
      <div class="t-dot"></div>
      <div class="t-dot"></div>
    </div>
  `;
  document.getElementById('chat-messages').appendChild(row);
  scrollChat();
  _typingEl = row;

  if (callback) setTimeout(() => { removeTyping(); callback(); }, delay);
}

function removeTyping() {
  const el = document.getElementById('__typing__');
  if (el) el.remove();
  _typingEl = null;
}

function appendToChat(el) {
  document.getElementById('chat-messages').appendChild(el);
  scrollChat();
}

function scrollChat() {
  const s = document.getElementById('chat-scroll');
  s.scrollTop = s.scrollHeight;
}


/* =============================================================
   HINT MODAL
   ============================================================= */

const HINTS = {
  behavioral : `<strong>Use the STAR method:</strong>
    <ul>
      <li><strong>S</strong>ituation — set the scene</li>
      <li><strong>T</strong>ask — what was your responsibility?</li>
      <li><strong>A</strong>ction — what did YOU specifically do?</li>
      <li><strong>R</strong>esult — what was the outcome? (use numbers if possible)</li>
    </ul>
    <br/>Keep it to 1-2 minutes. Be specific, not vague.`,
  technical  : `<strong>For technical questions:</strong>
    <ul>
      <li>Define the concept in your own words first</li>
      <li>Give a real example from your experience</li>
      <li>Mention any limitations or trade-offs</li>
      <li>It's okay to say "I'd look that up" for specifics</li>
    </ul>`,
  general    : `<strong>General tips:</strong>
    <ul>
      <li>Be concise — 1-3 short paragraphs is ideal</li>
      <li>Give concrete examples, not generic statements</li>
      <li>Stay relevant to the question asked</li>
    </ul>`
};

function showHint() {
  const q    = S.questions[S.currentQ] || {};
  const type = q.type || 'general';
  const hint = HINTS[type] || HINTS.general;

  document.getElementById('hint-body').innerHTML = hint;
  document.getElementById('hint-modal').classList.remove('hidden');
}

function closeHint() {
  document.getElementById('hint-modal').classList.add('hidden');
}


/* =============================================================
   REPORT SCREEN
   ============================================================= */

/** Fetches the final report from the server and renders it. */
async function finishInterview() {
  try {
    const res  = await fetch(`${API}/final-report`, {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify({ session_id: S.sessionId, qa_results: S.qaResults })
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error);
    showScreen('report');
    renderReport(data);
  } catch (err) {
    // Fallback: compute locally
    const scores = S.qaResults.map(r => r.score || 50);
    const avg    = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    showScreen('report');
    renderReport({ overall_score: avg, grade: gradeFromScore(avg), emoji: '🎉',
                   summary: `Completed with score ${avg}/100.`,
                   top_strengths: [], top_improvements: [] });
  }
}

/**
 * Populates all elements on the report screen.
 * @param {Object} d  Response from /api/final-report
 */
function renderReport(d) {
  const score = d.overall_score || 0;
  const grade = d.grade         || gradeFromScore(score);

  // Hero
  document.getElementById('rpt-emoji').textContent = d.emoji || '🎉';
  document.getElementById('rpt-title').textContent = 'Interview Complete!';
  document.getElementById('rpt-name').textContent  = S.candidateName;
  document.getElementById('rpt-grade').textContent  = grade;

  // Grade colour
  const gradeColors = { A: 'var(--c-green)', B: 'var(--c-gold)', C: 'var(--c-amber)', D: 'var(--c-red)' };
  document.getElementById('rpt-grade').style.color = gradeColors[grade] || 'var(--c-muted)';

  // Animate score ring
  animateRing(score);

  // Summary
  document.getElementById('rpt-summary').textContent = d.summary || '';

  // Strengths list
  const strEl = document.getElementById('rpt-strengths');
  strEl.innerHTML = '';
  (d.top_strengths || []).forEach(s => {
    const li = document.createElement('li');
    li.textContent = s;
    strEl.appendChild(li);
  });

  // Improvements list
  const impEl = document.getElementById('rpt-improvements');
  impEl.innerHTML = '';
  (d.top_improvements || []).forEach(s => {
    const li = document.createElement('li');
    li.textContent = s;
    impEl.appendChild(li);
  });

  // Q&A accordion
  renderAccordion();
}

/** Builds the per-question accordion on the report page. */
function renderAccordion() {
  const container = document.getElementById('qa-accordion');
  container.innerHTML = '';

  S.qaResults.forEach((r, i) => {
    const score = r.score || 0;
    let badgeClass = 'score-d';
    if (score >= 85) badgeClass = 'score-a';
    else if (score >= 70) badgeClass = 'score-b';
    else if (score >= 50) badgeClass = 'score-c';

    const item = document.createElement('div');
    item.className = 'qa-item';
    item.innerHTML = `
      <div class="qa-item-header" onclick="toggleAccordion(this)">
        <span class="qa-question">Q${i + 1}: ${escHtml(r.question)}</span>
        <span class="qa-score-badge ${badgeClass}">${score}/100</span>
        <span class="qa-chevron">▼</span>
      </div>
      <div class="qa-item-body">
        <p class="qa-answer-label">Your Answer</p>
        <p class="qa-answer-text">${escHtml(r.answer || '')}</p>
        <p class="qa-answer-label" style="margin-top:14px">AI Feedback</p>
        <p class="qa-feedback">${escHtml(r.feedback || '')}</p>
      </div>
    `;
    container.appendChild(item);
  });
}

/** Toggles an accordion item open/closed. */
function toggleAccordion(headerEl) {
  headerEl.closest('.qa-item').classList.toggle('open');
}

/**
 * Animates the SVG ring and score counter on the report page.
 * @param {number} target  Final score (0–100)
 */
function animateRing(target) {
  const circumference = 377;
  const arc = document.getElementById('ring-arc');

  // Set stroke colour
  let colour = 'var(--c-red)';
  if (target >= 85) colour = 'var(--c-green)';
  else if (target >= 70) colour = 'var(--c-gold)';
  else if (target >= 50) colour = 'var(--c-amber)';
  arc.style.stroke = colour;

  // Trigger transition: set offset after a tiny delay
  setTimeout(() => {
    arc.style.strokeDashoffset = circumference - (target / 100) * circumference;
  }, 100);

  // Count-up animation for the number
  const el = document.getElementById('rpt-score');
  let current = 0;
  const step  = Math.ceil(target / 50);
  const id = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) clearInterval(id);
  }, 25);
}


/* =============================================================
   HISTORY SCREEN
   ============================================================= */

/** Fetches all past sessions from /api/history and renders the table. */
async function loadHistory() {
  setActiveNav('history');
  showScreen('history');

  document.getElementById('history-loading').classList.remove('hidden');
  document.getElementById('history-table-wrap').classList.add('hidden');
  document.getElementById('history-empty').classList.add('hidden');

  try {
    const res  = await fetch(`${API}/history`);
    const data = await res.json();

    document.getElementById('history-loading').classList.add('hidden');

    const sessions = data.sessions || [];

    if (sessions.length === 0) {
      document.getElementById('history-empty').classList.remove('hidden');
      return;
    }

    // Build table rows
    const tbody = document.getElementById('history-tbody');
    tbody.innerHTML = '';

    sessions.forEach(s => {
      const score     = s.overall_score ?? '—';
      const grade     = s.grade         ?? '—';
      const summary   = (s.summary || '—').slice(0, 80) + (s.summary?.length > 80 ? '…' : '');
      const dateStr   = s.created_at ? new Date(s.created_at).toLocaleDateString() : '—';

      let scoreCls = '';
      if      (s.overall_score >= 85) scoreCls = 'score-a';
      else if (s.overall_score >= 70) scoreCls = 'score-b';
      else if (s.overall_score >= 50) scoreCls = 'score-c';
      else if (s.overall_score != null) scoreCls = 'score-d';

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${s.id}</td>
        <td><strong>${escHtml(s.candidate_name || '—')}</strong></td>
        <td><span class="qa-score-badge ${scoreCls}">${score}/100</span></td>
        <td>${grade}</td>
        <td style="max-width:280px;color:var(--c-muted);font-size:13px">${escHtml(summary)}</td>
        <td style="color:var(--c-muted);font-size:12px">${dateStr}</td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById('history-table-wrap').classList.remove('hidden');

  } catch (err) {
    document.getElementById('history-loading').innerHTML =
      `<span style="color:var(--c-red)">Failed to load history: ${escHtml(err.message)}</span>`;
  }
}


/* =============================================================
   UTILITY HELPERS
   ============================================================= */

/**
 * Shows one screen, hides all others.
 * @param {'upload'|'interview'|'report'|'history'} name
 */
function showScreen(name) {
  const map = {
    upload    : 'screen-upload',
    interview : 'screen-interview',
    report    : 'screen-report',
    history   : 'screen-history',
  };

  Object.values(map).forEach(id => {
    document.getElementById(id).classList.remove('active');
    document.getElementById(id).classList.add('hidden');
  });

  const target = map[name];
  if (target) {
    document.getElementById(target).classList.remove('hidden');
    document.getElementById(target).classList.add('active');
  }

  // Show/hide global header (hide during interview)
  const header = document.getElementById('site-header');
  header.style.display = name === 'interview' ? 'none' : '';

  // Highlight active nav button
  setActiveNav(name);
}

function setActiveNav(name) {
  document.getElementById('nav-upload') .classList.toggle('active', name === 'upload');
  document.getElementById('nav-history').classList.toggle('active', name === 'history');
}

/** Converts a score to a letter grade. */
function gradeFromScore(score) {
  if (score >= 85) return 'A';
  if (score >= 70) return 'B';
  if (score >= 55) return 'C';
  return 'D';
}

/**
 * Escapes HTML special characters to prevent XSS.
 * Always use this before inserting user-supplied text into innerHTML.
 */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

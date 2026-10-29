/**
 * ENERGY OPERATIONS ASSISTANT - CLIENT APPLICATION LOGIC
 * Rebuilt for high-reliability connection management, responsive state recovery,
 * safe DOM manipulation, and interactive energy domain operations.
 */

// Domain Icon SVGs for dynamic rendering
const ICONS = {
  solar: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C88924" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>`,
  wind: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3579B7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 12c-2-2.5-4-5-4-8a4 4 0 0 1 8 0c0 3-2 5.5-4 8z"/><path d="M12 12c2.5-2 5-4 8-4a4 4 0 0 1 0 8c-3 0-5.5-2-8-4z"/><path d="M12 12c-2.5 2-5 4-8 4a4 4 0 0 1 0-8c3 0 5.5 2 8 4z"/><circle cx="12" cy="12" r="1.5"/><path d="M12 13.5V22"/></svg>`,
  hydro: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#168C91" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>`,
  grid: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7561B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16M8 22l4-18 4 18M5 14h14M7 8h10"/></svg>`,
  document: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`,
  warning: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#A86C12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  error: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#B83A35" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`
};

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const inputEl = document.getElementById("operationalInput");
  const charCountEl = document.getElementById("charCountLabel");
  const submitBtn = document.getElementById("submitBtn");
  const resetBtn = document.getElementById("resetBtn");
  const intelContainer = document.getElementById("intelContentArea");
  const connectionDot = document.getElementById("connectionDot");
  const connectionStatusText = document.getElementById("connectionStatusText");
  const lastCheckedText = document.getElementById("lastCheckedText");
  const docCountNumber = document.getElementById("docCountNumber");
  const librarySummaryText = document.getElementById("librarySummaryText");
  const libraryCardsGrid = document.getElementById("libraryCardsGrid");

  // Keep reference to initial welcome HTML
  const initialWelcomeHTML = intelContainer.innerHTML;

  // Connection State variables
  let isBackendOnline = false;
  let isHealthChecking = false;
  let healthTimer = null;

  // =========================================================================
  // 1. Connection-State Management
  // =========================================================================

  function formatTime(date) {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    const strMinutes = minutes < 10 ? "0" + minutes : minutes;
    return `${hours}:${strMinutes} ${ampm}`;
  }

  async function checkBackendHealth() {
    if (isHealthChecking) return;
    isHealthChecking = true;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    try {
      const resp = await fetch("/api/health", { signal: controller.signal });
      clearTimeout(timeoutId);

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      isBackendOnline = true;
      connectionDot.className = "pulse-dot"; // green
      connectionStatusText.textContent = "Backend Online";
      lastCheckedText.textContent = `Last checked: ${formatTime(new Date())}`;

      if (data.indexed_documents !== undefined) {
        docCountNumber.textContent = data.indexed_documents;
      }
      if (data.indexed_chunks !== undefined) {
        librarySummaryText.textContent = `${data.indexed_documents || 4} documents • ${data.indexed_chunks || 4} chunks total`;
      }
    } catch (err) {
      clearTimeout(timeoutId);
      isBackendOnline = false;
      connectionDot.className = "pulse-dot offline"; // red
      connectionStatusText.textContent = "Backend Offline";
      lastCheckedText.textContent = "Disconnected (Retrying)";
    } finally {
      isHealthChecking = false;
      // Reschedule next check: 5s if offline to recover quickly, 12s if online
      clearTimeout(healthTimer);
      healthTimer = setTimeout(checkBackendHealth, isBackendOnline ? 12000 : 5000);
    }
  }

  // Load Document Catalog from API
  async function loadDocuments() {
    try {
      const resp = await fetch("/api/documents");
      if (!resp.ok) return;
      const data = await resp.json();
      if (data.documents && data.documents.length > 0) {
        renderLibraryCards(data.documents);
      }
    } catch (err) {
      // Keep initial static cards if fetch fails
    }
  }

  function getDomainClass(topic) {
    const t = (topic || "").toLowerCase();
    if (t.includes("solar")) return "solar";
    if (t.includes("wind")) return "wind";
    if (t.includes("hydro")) return "hydro";
    if (t.includes("grid")) return "grid";
    return "general";
  }

  function getDomainTag(topic) {
    const t = (topic || "").toLowerCase();
    if (t.includes("solar")) return "Solar";
    if (t.includes("wind")) return "Wind";
    if (t.includes("hydro")) return "Hydro";
    if (t.includes("grid")) return "Grid";
    return "Renewable";
  }

  function renderLibraryCards(docs) {
    libraryCardsGrid.textContent = "";

    docs.forEach(doc => {
      const domain = getDomainClass(doc.topic);
      const tag = getDomainTag(doc.topic);

      const card = document.createElement("div");
      card.className = `library-doc-card ${domain}`;
      card.setAttribute("tabindex", "0");
      card.setAttribute("role", "button");

      let defaultQuery = "What should be checked for inverter derating?";
      if (domain === "wind") defaultQuery = "How should gearbox vibration be investigated?";
      if (domain === "hydro") defaultQuery = "What checks are needed before spillway gate inspection?";
      if (domain === "grid") defaultQuery = "What factors should be reviewed for generation deviation?";
      card.setAttribute("data-query", defaultQuery);

      const art = document.createElement("div");
      art.className = "library-doc-art";
      art.setAttribute("aria-hidden", "true");
      art.innerHTML = ICONS[domain] || ICONS.document;

      const info = document.createElement("div");
      info.className = "library-doc-info";

      const tagSpan = document.createElement("span");
      tagSpan.className = `library-tag ${domain}`;
      tagSpan.textContent = tag;

      const title = document.createElement("div");
      title.className = "library-doc-title";
      title.textContent = doc.document_title;

      const file = document.createElement("div");
      file.className = "library-doc-file";
      file.textContent = doc.source_file;

      const meta = document.createElement("div");
      meta.className = "library-doc-meta";
      meta.textContent = `📄 ${doc.chunk_count} chunk(s)`;

      const chevron = document.createElement("div");
      chevron.className = "library-chevron";
      chevron.innerHTML = "&#8250;";

      info.appendChild(tagSpan);
      info.appendChild(title);
      info.appendChild(file);
      info.appendChild(meta);

      card.appendChild(art);
      card.appendChild(info);
      card.appendChild(chevron);

      // Click card to populate query
      card.addEventListener("click", () => {
        populateQuery(card.getAttribute("data-query"));
      });

      libraryCardsGrid.appendChild(card);
    });
  }

  // =========================================================================
  // 2. Input & Example Handling
  // =========================================================================

  function updateCharCount() {
    const len = inputEl.value.length;
    charCountEl.textContent = `${len} / 500`;
    if (len >= 500) {
      charCountEl.style.color = "var(--status-error)";
    } else {
      charCountEl.style.color = "var(--text-muted)";
    }
  }

  inputEl.addEventListener("input", updateCharCount);

  function populateQuery(text) {
    if (!text) return;
    inputEl.value = text;
    updateCharCount();
    inputEl.focus();
    inputEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // Domain Cards (Top Row) Click Event
  document.querySelectorAll(".domain-card").forEach(card => {
    card.addEventListener("click", () => {
      const q = card.getAttribute("data-query");
      populateQuery(q);
    });
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        populateQuery(card.getAttribute("data-query"));
      }
    });
  });

  // Example Question Buttons Click Event
  document.querySelectorAll(".example-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const q = btn.getAttribute("data-query");
      populateQuery(q);
    });
  });

  // Reset / Clear Button
  resetBtn.addEventListener("click", () => {
    inputEl.value = "";
    updateCharCount();
    intelContainer.innerHTML = initialWelcomeHTML;
    inputEl.focus();
  });

  // Keyboard shortcut: Ctrl+Enter or Cmd+Enter to submit
  inputEl.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleFormSubmit();
    }
  });

  // Submit Button
  submitBtn.addEventListener("click", handleFormSubmit);

  // =========================================================================
  // 3. Query Submission & Rendering
  // =========================================================================

  async function handleFormSubmit() {
    const query = inputEl.value.trim();

    if (!query) {
      renderAlert(
        "Empty Question",
        "Please enter an operational question or select one of the examples above.",
        "warning"
      );
      inputEl.focus();
      return;
    }

    if (query.length > 500) {
      renderAlert(
        "Input Length Exceeded",
        "Question must not exceed 500 characters.",
        "error"
      );
      return;
    }

    // Set Loading State
    setLoadingState(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    try {
      const resp = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: query, top_k: 3 }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        const msg = errJson.detail || `Server error (${resp.status})`;
        renderAlert("Operational Query Error", msg, "error");
        return;
      }

      const data = await resp.json();
      renderResponse(data);
    } catch (err) {
      clearTimeout(timeoutId);
      const isTimeout = err.name === "AbortError";
      renderAlert(
        isTimeout ? "Request Timeout" : "Connection Error",
        isTimeout
          ? "The operational query request timed out. Please verify server responsiveness."
          : "Unable to reach the Energy Operations backend. Please verify that the FastAPI server is running.",
        "error"
      );
    } finally {
      setLoadingState(false);
    }
  }

  function setLoadingState(loading) {
    submitBtn.disabled = loading;
    if (loading) {
      intelContainer.textContent = "";

      const view = document.createElement("div");
      view.className = "loading-view";

      const spinner = document.createElement("div");
      spinner.className = "spinner-circle";

      const title = document.createElement("div");
      title.className = "loading-heading";
      title.textContent = "Searching indexed operational documents...";

      const sub = document.createElement("div");
      sub.className = "loading-detail";
      sub.textContent = "Computing TF-IDF vector similarity and ranking evidence passages.";

      view.appendChild(spinner);
      view.appendChild(title);
      view.appendChild(sub);
      intelContainer.appendChild(view);
    }
  }

  function renderAlert(titleText, msgText, type = "warning") {
    intelContainer.textContent = "";

    const alertBox = document.createElement("div");
    alertBox.className = `system-alert ${type}`;

    const iconBox = document.createElement("div");
    iconBox.innerHTML = type === "error" ? ICONS.error : ICONS.warning;

    const content = document.createElement("div");
    const title = document.createElement("div");
    title.className = "system-alert-title";
    title.textContent = titleText;

    const msg = document.createElement("div");
    msg.className = "system-alert-msg";
    msg.textContent = msgText;

    content.appendChild(title);
    content.appendChild(msg);

    alertBox.appendChild(iconBox);
    alertBox.appendChild(content);
    intelContainer.appendChild(alertBox);
  }

  function renderResponse(data) {
    intelContainer.textContent = "";

    const wrapper = document.createElement("div");
    wrapper.className = "response-view";

    // 1. Response Meta Bar
    const metaBar = document.createElement("div");
    metaBar.className = "response-meta-bar";

    const topicTag = document.createElement("div");
    const domain = getDomainClass(data.matched_topic);
    topicTag.className = `topic-tag ${domain}`;
    topicTag.innerHTML = `${ICONS[domain] || ICONS.document} <span>${data.matched_topic || (data.status === "success" ? "Operational Intelligence" : "Unmatched Query")}</span>`;

    const perfBadge = document.createElement("div");
    perfBadge.className = "perf-badge";
    perfBadge.textContent = `Latency: ${data.latency_ms} ms • Status: ${data.status.replace("_", " ").toUpperCase()}`;

    metaBar.appendChild(topicTag);
    metaBar.appendChild(perfBadge);
    wrapper.appendChild(metaBar);

    // 2. Insufficient Evidence Case
    if (data.status === "insufficient_evidence") {
      const alert = document.createElement("div");
      alert.className = "system-alert warning";

      const icon = document.createElement("div");
      icon.innerHTML = ICONS.warning;

      const body = document.createElement("div");
      const title = document.createElement("div");
      title.className = "system-alert-title";
      title.textContent = "Insufficient Evidence in Local Documentation";

      const text = document.createElement("div");
      text.className = "system-alert-msg";
      text.textContent = data.result;

      body.appendChild(title);
      body.appendChild(text);
      alert.appendChild(icon);
      alert.appendChild(body);
      wrapper.appendChild(alert);

      // Disclaimer Banner
      renderDisclaimer(wrapper, data.disclaimer);
      intelContainer.appendChild(wrapper);
      return;
    }

    // 3. Grounded Answer Card
    const answerCard = document.createElement("div");
    answerCard.className = "answer-card";

    const cardTitle = document.createElement("div");
    cardTitle.className = "answer-card-title";
    cardTitle.textContent = "Grounded Operational Response";

    const cardBody = document.createElement("div");
    cardBody.className = "answer-card-body";
    cardBody.textContent = data.result;

    answerCard.appendChild(cardTitle);
    answerCard.appendChild(cardBody);
    wrapper.appendChild(answerCard);

    // 4. Safety Disclaimer Banner
    renderDisclaimer(wrapper, data.disclaimer);

    // 5. Citations Panel
    if (data.citations && data.citations.length > 0) {
      const citationsSection = document.createElement("div");
      citationsSection.className = "citations-wrapper";

      const headingRow = document.createElement("div");
      headingRow.className = "citations-heading-row";
      headingRow.textContent = `Traceable Citations (${data.citations.length})`;
      citationsSection.appendChild(headingRow);

      data.citations.forEach(cit => {
        const tile = document.createElement("div");
        tile.className = "citation-tile";

        const headerLine = document.createElement("div");
        headerLine.className = "citation-header-line";

        const source = document.createElement("div");
        source.className = "citation-source-name";
        source.innerHTML = `${ICONS.document} <span>${cit.document_title} (${cit.source_file})</span>`;

        const scorePill = document.createElement("div");
        scorePill.className = "citation-score-pill";
        scorePill.textContent = `Score: ${(cit.similarity_score * 100).toFixed(1)}%`;

        headerLine.appendChild(source);
        headerLine.appendChild(scorePill);

        const quote = document.createElement("div");
        quote.className = "citation-quote";
        quote.textContent = `"${cit.excerpt}"`;

        const chunk = document.createElement("div");
        chunk.className = "citation-chunk-id";
        chunk.textContent = `Chunk ID: ${cit.chunk_id}`;

        tile.appendChild(headerLine);
        tile.appendChild(quote);
        tile.appendChild(chunk);
        citationsSection.appendChild(tile);
      });

      wrapper.appendChild(citationsSection);
    }

    intelContainer.appendChild(wrapper);
  }

  function renderDisclaimer(container, text) {
    const box = document.createElement("div");
    box.className = "system-alert warning";
    box.style.marginTop = "4px";

    const icon = document.createElement("div");
    icon.innerHTML = ICONS.warning;

    const content = document.createElement("div");
    const msg = document.createElement("div");
    msg.className = "system-alert-msg";
    msg.textContent = text;

    content.appendChild(msg);
    box.appendChild(icon);
    box.appendChild(content);
    container.appendChild(box);
  }

  // =========================================================================
  // 4. Initialization
  // =========================================================================
  checkBackendHealth();
  loadDocuments();
});

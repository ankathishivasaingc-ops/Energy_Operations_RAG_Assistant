/**
 * Energy Operations Assistant - Client Application Logic
 * Implements safe DOM construction, live connectivity polling,
 * example question handlers, and real-time RAG response rendering.
 */

// Domain SVGs
const ICONS = {
  solar: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`,
  wind: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 12c-2-2.5-4-5-4-8a4 4 0 0 1 8 0c0 3-2 5.5-4 8z"/><path d="M12 12c2.5-2 5-4 8-4a4 4 0 0 1 0 8c-3 0-5.5-2-8-4z"/><path d="M12 12c-2.5 2-5 4-8 4a4 4 0 0 1 0-8c3 0 5.5 2 8 4z"/><circle cx="12" cy="12" r="1.5"/><path d="M12 13.5V22"/></svg>`,
  hydro: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>`,
  grid: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16"/><path d="M8 22l4-18 4 18"/><path d="M5 14h14"/><path d="M7 8h10"/></svg>`,
  document: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`,
  warning: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`
};

document.addEventListener("DOMContentLoaded", () => {
  const queryInput = document.getElementById("queryInput");
  const charCount = document.getElementById("charCount");
  const askBtn = document.getElementById("askBtn");
  const clearBtn = document.getElementById("clearBtn");
  const resultsContainer = document.getElementById("resultsContainer");
  const connectionDot = document.getElementById("connectionDot");
  const connectionText = document.getElementById("connectionText");
  const docCountText = document.getElementById("docCountText");
  const catalogList = document.getElementById("catalogList");

  // Track state
  let isConnected = false;

  // Real-time character counter
  queryInput.addEventListener("input", () => {
    const len = queryInput.value.length;
    charCount.textContent = `${len} / 500`;
    if (len > 500) {
      charCount.style.color = "var(--text-error)";
    } else {
      charCount.style.color = "var(--text-secondary)";
    }
  });

  // Example question buttons
  document.querySelectorAll(".example-chip").forEach(button => {
    button.addEventListener("click", () => {
      const q = button.getAttribute("data-query");
      queryInput.value = q;
      queryInput.dispatchEvent(new Event("input"));
      queryInput.focus();
      handleQuerySubmit();
    });
  });

  // Clear button
  clearBtn.addEventListener("click", () => {
    queryInput.value = "";
    queryInput.dispatchEvent(new Event("input"));
    renderEmptyState();
    queryInput.focus();
  });

  // Submit on primary button click
  askBtn.addEventListener("click", handleQuerySubmit);

  // Submit on Ctrl+Enter or Cmd+Enter
  queryInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleQuerySubmit();
    }
  });

  // Initial data and health polling
  checkBackendHealth();
  loadDocumentCatalog();
  setInterval(checkBackendHealth, 15000);

  // Backend Health check
  async function checkBackendHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("Health check returned status " + res.status);
      const data = await res.json();
      isConnected = true;
      connectionDot.classList.remove("disconnected");
      connectionText.textContent = "Backend Connected";
      docCountText.textContent = `${data.indexed_documents || 4} SOPs Indexed`;
    } catch (err) {
      isConnected = false;
      connectionDot.classList.add("disconnected");
      connectionText.textContent = "Offline / Connecting...";
      docCountText.textContent = "Disconnected";
    }
  }

  // Load Document Catalog
  async function loadDocumentCatalog() {
    try {
      const res = await fetch("/api/documents");
      if (!res.ok) return;
      const data = await res.json();
      renderCatalog(data.documents || []);
    } catch (err) {
      // Keep static placeholder if fetch fails
    }
  }

  function getIconForTopic(topic) {
    const t = (topic || "").toLowerCase();
    if (t.includes("solar")) return ICONS.solar;
    if (t.includes("wind")) return ICONS.wind;
    if (t.includes("hydro")) return ICONS.hydro;
    if (t.includes("grid")) return ICONS.grid;
    return ICONS.document;
  }

  function renderCatalog(docs) {
    if (!catalogList) return;
    catalogList.textContent = "";

    docs.forEach(doc => {
      const card = document.createElement("div");
      card.className = "catalog-card";

      const iconBox = document.createElement("div");
      iconBox.className = "catalog-icon";
      iconBox.innerHTML = getIconForTopic(doc.topic);

      const info = document.createElement("div");
      info.className = "catalog-info";

      const title = document.createElement("div");
      title.className = "catalog-title";
      title.textContent = doc.document_title;

      const meta = document.createElement("div");
      meta.className = "catalog-meta";
      meta.textContent = `${doc.source_file} • ${doc.chunk_count} chunk(s)`;

      info.appendChild(title);
      info.appendChild(meta);
      card.appendChild(iconBox);
      card.appendChild(info);
      catalogList.appendChild(card);
    });
  }

  // Execute RAG Query
  async function handleQuerySubmit() {
    const query = queryInput.value.trim();

    if (!query) {
      renderAlert("Empty Question", "Please type an operational question or select an example above.", "warning");
      queryInput.focus();
      return;
    }

    if (query.length > 500) {
      renderAlert("Input Limit Exceeded", "Questions are limited to 500 characters.", "error");
      return;
    }

    // Set loading state
    setLoading(true);

    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: query, top_k: 3 }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const msg = errorData.detail || `Server returned error (${response.status})`;
        renderAlert("Validation or Processing Error", msg, "error");
        return;
      }

      const data = await response.json();
      renderResponse(data);
    } catch (err) {
      renderAlert(
        "Connection Error",
        "Unable to reach the Energy Operations backend. Please verify that the FastAPI server is running.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  }

  function setLoading(loading) {
    askBtn.disabled = loading;
    if (loading) {
      resultsContainer.textContent = "";
      const loadingState = document.createElement("div");
      loadingState.className = "loading-state";

      const spinner = document.createElement("div");
      spinner.className = "spinner";

      const text = document.createElement("div");
      text.className = "loading-text";
      text.textContent = "Scanning Indexed Operational Documents...";

      const subtext = document.createElement("div");
      subtext.className = "loading-subtext";
      subtext.textContent = "Computing TF-IDF vector similarity and ranking evidence passages.";

      loadingState.appendChild(spinner);
      loadingState.appendChild(text);
      loadingState.appendChild(subtext);
      resultsContainer.appendChild(loadingState);
    }
  }

  function renderEmptyState() {
    resultsContainer.textContent = "";
    const empty = document.createElement("div");
    empty.className = "empty-state";

    const icon = document.createElement("div");
    icon.className = "empty-icon";
    icon.innerHTML = `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;

    const title = document.createElement("div");
    title.className = "empty-title";
    title.textContent = "Ready for Operational Inquiries";

    const desc = document.createElement("div");
    desc.className = "empty-desc";
    desc.textContent = "Enter a question regarding solar inverter derating, wind turbine vibrations, hydro spillway gate safety, or grid deviations.";

    empty.appendChild(icon);
    empty.appendChild(title);
    empty.appendChild(desc);
    resultsContainer.appendChild(empty);
  }

  function renderAlert(titleText, msgText, type = "warning") {
    resultsContainer.textContent = "";
    const alertBox = document.createElement("div");
    alertBox.className = `alert-box ${type}`;

    const icon = document.createElement("div");
    icon.innerHTML = ICONS.warning;

    const body = document.createElement("div");
    const title = document.createElement("div");
    title.className = "alert-title";
    title.textContent = titleText;

    const msg = document.createElement("div");
    msg.className = "alert-msg";
    msg.textContent = msgText;

    body.appendChild(title);
    body.appendChild(msg);
    alertBox.appendChild(icon);
    alertBox.appendChild(body);
    resultsContainer.appendChild(alertBox);
  }

  function renderResponse(data) {
    resultsContainer.textContent = "";
    const wrapper = document.createElement("div");
    wrapper.className = "result-content";

    // 1. Meta Bar (Topic & Latency)
    const metaBar = document.createElement("div");
    metaBar.className = "result-meta-bar";

    const topicBadge = document.createElement("div");
    topicBadge.className = "topic-badge";

    const topicIcon = document.createElement("span");
    topicIcon.innerHTML = getIconForTopic(data.matched_topic);
    const topicText = document.createElement("span");
    topicText.textContent = data.matched_topic || (data.status === "success" ? "Renewable Operations" : "Unmatched Query");

    topicBadge.appendChild(topicIcon);
    topicBadge.appendChild(topicText);

    const perfPill = document.createElement("div");
    perfPill.className = "perf-pill";
    perfPill.textContent = `Latency: ${data.latency_ms} ms • Status: ${data.status.replace("_", " ").toUpperCase()}`;

    metaBar.appendChild(topicBadge);
    metaBar.appendChild(perfPill);
    wrapper.appendChild(metaBar);

    // 2. Insufficient Evidence Case
    if (data.status === "insufficient_evidence") {
      const alertBox = document.createElement("div");
      alertBox.className = "alert-box warning";

      const icon = document.createElement("div");
      icon.innerHTML = ICONS.warning;

      const body = document.createElement("div");
      const title = document.createElement("div");
      title.className = "alert-title";
      title.textContent = "Insufficient Evidence in Local Documentation";

      const msg = document.createElement("div");
      msg.className = "alert-msg";
      msg.textContent = data.result;

      body.appendChild(title);
      body.appendChild(msg);
      alertBox.appendChild(icon);
      alertBox.appendChild(body);
      wrapper.appendChild(alertBox);

      // Disclaimer Banner
      renderDisclaimer(wrapper, data.disclaimer);
      resultsContainer.appendChild(wrapper);
      return;
    }

    // 3. Grounded Answer Box
    const answerBox = document.createElement("div");
    answerBox.className = "answer-box";

    const answerLabel = document.createElement("div");
    answerLabel.className = "answer-label";
    answerLabel.textContent = "Grounded Operational Response";

    const answerText = document.createElement("div");
    answerText.className = "answer-text";
    answerText.textContent = data.result;

    answerBox.appendChild(answerLabel);
    answerBox.appendChild(answerText);
    wrapper.appendChild(answerBox);

    // 4. Disclaimer Banner
    renderDisclaimer(wrapper, data.disclaimer);

    // 5. Citations Panel
    if (data.citations && data.citations.length > 0) {
      const citationsPanel = document.createElement("div");
      citationsPanel.className = "citations-panel";

      const citationsHeader = document.createElement("div");
      citationsHeader.className = "citations-header";
      citationsHeader.textContent = `Traceable Citations (${data.citations.length})`;
      citationsPanel.appendChild(citationsHeader);

      data.citations.forEach((cit, idx) => {
        const card = document.createElement("div");
        card.className = "citation-card";

        const top = document.createElement("div");
        top.className = "citation-top";

        const source = document.createElement("div");
        source.className = "citation-source";
        source.innerHTML = `${ICONS.document} <span>${cit.document_title} (${cit.source_file})</span>`;

        const scoreBadge = document.createElement("div");
        scoreBadge.className = "citation-score-badge";
        scoreBadge.textContent = `Similarity: ${(cit.similarity_score * 100).toFixed(1)}%`;

        top.appendChild(source);
        top.appendChild(scoreBadge);

        const excerpt = document.createElement("div");
        excerpt.className = "citation-excerpt";
        excerpt.textContent = `"${cit.excerpt}"`;

        const chunkId = document.createElement("div");
        chunkId.className = "citation-chunk-id";
        chunkId.textContent = `Chunk ID: ${cit.chunk_id}`;

        card.appendChild(top);
        card.appendChild(excerpt);
        card.appendChild(chunkId);
        citationsPanel.appendChild(card);
      });

      wrapper.appendChild(citationsPanel);
    }

    resultsContainer.appendChild(wrapper);
  }

  function renderDisclaimer(container, text) {
    const disclaimer = document.createElement("div");
    disclaimer.className = "disclaimer-banner";

    const icon = document.createElement("div");
    icon.className = "disclaimer-icon";
    icon.innerHTML = ICONS.warning;

    const disclaimerText = document.createElement("div");
    disclaimerText.textContent = text;

    disclaimer.appendChild(icon);
    disclaimer.appendChild(disclaimerText);
    container.appendChild(disclaimer);
  }
});

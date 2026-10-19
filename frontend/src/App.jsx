import { useEffect, useMemo, useState } from "react";

const API_URL = "http://127.0.0.1:8000/api";

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status}).`);
  }

  return response.json();
}

function formatStatus(status) {
  return String(status || "uploaded").replaceAll("_", " ");
}

function statusClass(status) {
  if (status === "completed") return "status success";
  if (status === "failed") return "status danger";
  return "status pending";
}

function riskClass(severity) {
  if (severity === "high") return "risk high";
  if (severity === "medium") return "risk medium";
  return "risk low";
}

function getConfidence(flag) {
  const value = Number(flag.confidence);
  return Number.isFinite(value) && value > 0
    ? Math.round(value * 100)
    : null;
}

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);

  const [metrics, setMetrics] = useState([]);
  const [redFlags, setRedFlags] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [report, setReport] = useState(null);

  const [chatMessages, setChatMessages] = useState([]);
  const [question, setQuestion] = useState("");

  const [sessionName, setSessionName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [fiscalYear, setFiscalYear] = useState("");
  const [pdfFile, setPdfFile] = useState(null);

  const [activeView, setActiveView] = useState("dashboard");
  const [showUpload, setShowUpload] = useState(false);
  const [showSessionForm, setShowSessionForm] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);

  const completedDocuments = useMemo(
    () => documents.filter((document) => document.status === "completed"),
    [documents]
  );

  const selectedReports = useMemo(
    () => documents.filter((document) => selectedIds.includes(document.id)),
    [documents, selectedIds]
  );

  const highRiskCount = useMemo(
    () => redFlags.filter((flag) => flag.severity === "high").length,
    [redFlags]
  );

  const totalChunks = useMemo(
    () => documents.reduce((total, document) => total + (document.chunk_count || 0), 0),
    [documents]
  );

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      const data = await api("/sessions");
      setSessions(data);

      if (!selectedSession && data.length > 0) {
        await chooseSession(data[0]);
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function loadDocuments(sessionId) {
    try {
      const data = await api(`/documents/session/${sessionId}`);
      setDocuments(data);
      return data;
    } catch (requestError) {
      setDocuments([]);
      setError(requestError.message);
      return [];
    }
  }

  async function chooseSession(session) {
    setSelectedSession(session);
    setSelectedDocument(null);
    setMetrics([]);
    setRedFlags([]);
    setComparison(null);
    setReport(null);
    setChatMessages([]);
    setError("");
    setMessage("");

    const data = await loadDocuments(session.id);

    setSelectedIds(
      data
        .filter((document) => document.status === "completed")
        .map((document) => document.id)
    );
  }

  async function createSession(event) {
    event.preventDefault();

    if (!sessionName.trim()) {
      setError("Enter a name for the research workspace.");
      return;
    }

    try {
      setProcessing(true);
      setError("");

      const session = await api("/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: sessionName.trim(),
          description: "Financial research workspace",
        }),
      });

      setSessionName("");
      setShowSessionForm(false);
      await loadSessions();
      await chooseSession(session);
      setMessage("New research workspace created.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setProcessing(false);
    }
  }

  async function openDocument(document) {
    setSelectedDocument(document);
    setMetrics([]);
    setRedFlags([]);
    setReport(null);
    setError("");
    setMessage("Loading analysis results...");

    try {
      const [metricData, flagData] = await Promise.all([
        api(`/documents/${document.id}/metrics`),
        api(`/documents/${document.id}/red-flags`),
      ]);

      setMetrics(metricData);
      setRedFlags(flagData);

      if (metricData.length === 0) {
        setMessage("No financial metrics were extracted from this report.");
      } else {
        setMessage("Analysis results loaded successfully.");
      }

      setActiveView("workspace");
    } catch (requestError) {
      setError(`Could not load report output: ${requestError.message}`);
    }
  }

  async function uploadDocument(event) {
    event.preventDefault();

    if (!selectedSession) {
      setError("Create or select a workspace first.");
      return;
    }

    if (!pdfFile) {
      setError("Select a company annual-report PDF.");
      return;
    }

    if (pdfFile.type && pdfFile.type !== "application/pdf") {
      setError(
        "Only Annual Report, Form 10-K, Form 20-F, or annual financial-report PDF files are allowed."
      );
      return;
    }

    try {
      setProcessing(true);
      setError("");
      setMessage(
        "Validating report and running Document, Extraction, and Red Flag Agents..."
      );

      const formData = new FormData();
      formData.append("session_id", selectedSession.id);
      formData.append("company_name", companyName.trim());
      formData.append("fiscal_year", fiscalYear.trim());
      formData.append("file", pdfFile);

      const uploadedDocument = await api("/documents/upload", {
        method: "POST",
        body: formData,
      });

      setCompanyName("");
      setFiscalYear("");
      setPdfFile(null);
      setShowUpload(false);

      const data = await loadDocuments(selectedSession.id);

      setSelectedIds(
        data
          .filter((document) => document.status === "completed")
          .map((document) => document.id)
      );

      await openDocument(uploadedDocument);
      setMessage("Annual report verified and analysed successfully.");
    } catch (requestError) {
      setError(`Upload rejected: ${requestError.message}`);
    } finally {
      setProcessing(false);
    }
  }

  async function reprocessDocument() {
    if (!selectedDocument) return;

    try {
      setProcessing(true);
      setError("");
      setMessage(
        "Reprocessing: Document Agent → Extraction Agent → Red Flag Agent..."
      );

      const updatedDocument = await api(
        `/documents/${selectedDocument.id}/reprocess`,
        { method: "POST" }
      );

      await loadDocuments(selectedSession.id);
      await openDocument(updatedDocument);
      setMessage("Report reprocessed successfully.");
    } catch (requestError) {
      setError(`Reprocessing failed: ${requestError.message}`);
    } finally {
      setProcessing(false);
    }
  }

  function toggleSelectedDocument(documentId) {
    setSelectedIds((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId]
    );
  }

  async function askResearch(event) {
    event.preventDefault();

    if (!question.trim()) {
      setError("Enter a research question.");
      return;
    }

    if (selectedIds.length === 0) {
      setError("Select at least one completed annual report.");
      return;
    }

    const userMessage = {
      role: "user",
      content: question.trim(),
    };

    try {
      setProcessing(true);
      setError("");

      setChatMessages((current) => [...current, userMessage]);

      const result = await api("/analysis/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMessage.content,
          document_ids: selectedIds,
          history: chatMessages.slice(-8),
        }),
      });

      setChatMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: result.answer,
          citations: result.citations || [],
          reasoningSteps: result.reasoning_steps || [],
          metrics: result.metrics || [],
        },
      ]);

      setQuestion("");
      setMessage("Research Agent generated a source-grounded response.");
    } catch (requestError) {
      setError(`Research Agent error: ${requestError.message}`);
    } finally {
      setProcessing(false);
    }
  }

  async function compareReports() {
    if (selectedIds.length < 2) {
      setError("Select at least two completed reports to compare.");
      return;
    }

    try {
      setProcessing(true);
      setError("");
      setMessage("Comparison Agent is building a peer benchmark...");

      const result = await api("/analysis/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_ids: selectedIds }),
      });

      setComparison(result);
      setActiveView("comparison");
      setMessage("Peer comparison generated.");
    } catch (requestError) {
      setError(`Comparison Agent error: ${requestError.message}`);
    } finally {
      setProcessing(false);
    }
  }

  async function generateReport() {
    if (!selectedDocument) {
      setError("Open a completed annual report first.");
      return;
    }

    try {
      setProcessing(true);
      setError("");

      const result = await api(`/analysis/report/${selectedDocument.id}`);
      setReport(result);
      setActiveView("report");
      setMessage("Analyst report summary generated.");
    } catch (requestError) {
      setError(`Report Agent error: ${requestError.message}`);
    } finally {
      setProcessing(false);
    }
  }

  function navigate(view) {
    setActiveView(view);
    setError("");
  }

  return (
    <div className="application">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">F</div>
          <div>
            <span>FINANCE AI</span>
            <strong>Research Hub</strong>
          </div>
        </div>

        <nav className="navigation">
          <button
            className={activeView === "dashboard" ? "nav-item active" : "nav-item"}
            onClick={() => navigate("dashboard")}
          >
            <span>▦</span> Dashboard
          </button>

          <button
            className={activeView === "workspace" ? "nav-item active" : "nav-item"}
            onClick={() => navigate("workspace")}
          >
            <span>◫</span> Report Workspace
          </button>

          <button
            className={activeView === "research" ? "nav-item active" : "nav-item"}
            onClick={() => navigate("research")}
          >
            <span>◌</span> Research Chat
          </button>

          <button
            className={activeView === "comparison" ? "nav-item active" : "nav-item"}
            onClick={() => navigate("comparison")}
          >
            <span>⇄</span> Comparison
          </button>

          <button
            className={activeView === "report" ? "nav-item active" : "nav-item"}
            onClick={() => navigate("report")}
          >
            <span>▤</span> Analyst Report
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="agent-status">
            <span className="pulse" />
            <div>
              <strong>Agents Online</strong>
              <small>Document · Extraction · Risk</small>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="breadcrumb">
              Financial Research / {selectedSession?.name || "No Workspace"}
            </p>
            <h1>
              {activeView === "dashboard" && "Research Dashboard"}
              {activeView === "workspace" && "Annual Report Workspace"}
              {activeView === "research" && "Ask the Research Agent"}
              {activeView === "comparison" && "Company Comparison"}
              {activeView === "report" && "Analyst-Style Report"}
            </h1>
          </div>

          <div className="topbar-actions">
            <button
              className="button secondary"
              onClick={() => setShowSessionForm(true)}
            >
              + New Workspace
            </button>

            <button
              className="button primary"
              disabled={!selectedSession || processing}
              onClick={() => setShowUpload(true)}
            >
              + Upload Report
            </button>
          </div>
        </header>

        {message && (
          <div className="toast success-toast">
            <span>✓</span>
            <p>{message}</p>
            <button onClick={() => setMessage("")}>×</button>
          </div>
        )}

        {error && (
          <div className="toast error-toast">
            <span>!</span>
            <p>{error}</p>
            <button onClick={() => setError("")}>×</button>
          </div>
        )}

        {!selectedSession ? (
          <section className="welcome-card">
            <div className="welcome-icon">⌁</div>
            <h2>Create your first research workspace</h2>
            <p>
              Create a workspace, upload company annual reports, and let the
              multi-agent pipeline extract financial insights.
            </p>
            <button
              className="button primary large"
              onClick={() => setShowSessionForm(true)}
            >
              Create Research Workspace
            </button>
          </section>
        ) : (
          <>
            {activeView === "dashboard" && (
              <>
                <section className="hero-card">
                  <div>
                    <p className="section-label">ACTIVE WORKSPACE</p>
                    <h2>{selectedSession.name}</h2>
                    <p>
                      Upload annual reports, identify financial risks, compare
                      companies, and ask grounded research questions.
                    </p>
                  </div>

                  <div className="hero-card-actions">
                    <button
                      className="button primary"
                      onClick={() => setShowUpload(true)}
                    >
                      Upload Annual Report
                    </button>
                    <button
                      className="button ghost"
                      onClick={() => navigate("research")}
                    >
                      Ask Research Agent
                    </button>
                  </div>
                </section>

                <section className="stat-grid">
                  <article className="stat-card blue">
                    <div className="stat-icon">◫</div>
                    <div>
                      <span>Annual Reports</span>
                      <strong>{documents.length}</strong>
                      <small>{completedDocuments.length} completed</small>
                    </div>
                  </article>

                  <article className="stat-card purple">
                    <div className="stat-icon">⌘</div>
                    <div>
                      <span>Indexed Chunks</span>
                      <strong>{totalChunks}</strong>
                      <small>Available for retrieval</small>
                    </div>
                  </article>

                  <article className="stat-card orange">
                    <div className="stat-icon">⚑</div>
                    <div>
                      <span>Risk Signals</span>
                      <strong>{redFlags.length}</strong>
                      <small>{highRiskCount} high-priority signals</small>
                    </div>
                  </article>

                  <article className="stat-card green">
                    <div className="stat-icon">◌</div>
                    <div>
                      <span>Research Scope</span>
                      <strong>{selectedIds.length}</strong>
                      <small>Reports selected</small>
                    </div>
                  </article>
                </section>

                <section className="content-card">
                  <div className="card-heading">
                    <div>
                      <p className="section-label">DOCUMENT LIBRARY</p>
                      <h2>Annual Reports</h2>
                    </div>

                    <button
                      className="text-button"
                      onClick={() => loadDocuments(selectedSession.id)}
                    >
                      Refresh List ↻
                    </button>
                  </div>

                  {documents.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-icon">↑</div>
                      <h3>No annual reports uploaded</h3>
                      <p>
                        Upload a verified company annual report to begin
                        financial analysis.
                      </p>
                      <button
                        className="button primary"
                        onClick={() => setShowUpload(true)}
                      >
                        Upload First Report
                      </button>
                    </div>
                  ) : (
                    <div className="report-list">
                      {documents.map((document) => (
                        <article className="report-row" key={document.id}>
                          <label className="selection-box">
                            <input
                              type="checkbox"
                              disabled={document.status !== "completed"}
                              checked={selectedIds.includes(document.id)}
                              onChange={() => toggleSelectedDocument(document.id)}
                            />
                            <span />
                          </label>

                          <div className="file-icon">PDF</div>

                          <div className="report-info">
                            <strong>{document.original_filename}</strong>
                            <span>
                              {document.company_name || "Unknown Company"} ·{" "}
                              {document.fiscal_year || "Annual Report"}
                            </span>
                          </div>

                          <div className="report-stat">
                            <strong>{document.page_count || 0}</strong>
                            <span>Pages</span>
                          </div>

                          <div className="report-stat">
                            <strong>{document.chunk_count || 0}</strong>
                            <span>Chunks</span>
                          </div>

                          <span className={statusClass(document.status)}>
                            {formatStatus(document.status)}
                          </span>

                          <button
                            className="icon-button"
                            title="Open annual report analysis"
                            onClick={() => openDocument(document)}
                          >
                            →
                          </button>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              </>
            )}

            {activeView === "workspace" && (
              <section className="workspace-layout">
                {!selectedDocument ? (
                  <div className="empty-state content-card">
                    <div className="empty-icon">◫</div>
                    <h3>Select an annual report</h3>
                    <p>
                      Open a completed report from the Dashboard to view
                      financial metrics and red-flag analysis.
                    </p>
                    <button
                      className="button primary"
                      onClick={() => navigate("dashboard")}
                    >
                      Open Dashboard
                    </button>
                  </div>
                ) : (
                  <>
                    <section className="content-card document-viewer">
  ...
  <iframe
    title="Annual report PDF"
    src={`${API_URL}/documents/${selectedDocument.id}/file`}
  />
</section>

                    <section className="analysis-column">
                      <section className="content-card">
                        <div className="card-heading">
                          <div>
                            <p className="section-label">EXTRACTION AGENT</p>
                            <h2>Key Financial Metrics</h2>
                          </div>

                          <button
                            className="text-button"
                            onClick={generateReport}
                            disabled={processing}
                          >
                            Generate Report →
                          </button>
                        </div>

                        {metrics.length === 0 ? (
                          <div className="empty-mini">
                            No values were extracted. Try reprocessing a
                            text-based annual report.
                          </div>
                        ) : (
                          <div className="metric-grid">
                            {metrics.map((metric) => (
                              <article className="metric-card" key={metric.id}>
                                <span>{metric.metric_name}</span>
                                <strong>{metric.metric_value}</strong>
                                <small>
                                  {metric.period || "Annual Report"} · Page{" "}
                                  {metric.source_page}
                                </small>
                                <a
                                  href={`${API_URL}/documents/${selectedDocument.id}/file#page=${metric.source_page}`}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  View evidence →
                                </a>
                              </article>
                            ))}
                          </div>
                        )}
                      </section>

                      <section className="content-card">
                        <div className="card-heading">
                          <div>
                            <p className="section-label">RED FLAG AGENT</p>
                            <h2>Risk Intelligence</h2>
                          </div>

                          <span className="risk-total">
                            {redFlags.length} Signals
                          </span>
                        </div>

                        {redFlags.length === 0 ? (
                          <div className="empty-mini">
                            No configured warning signals were found in the
                            readable PDF text.
                          </div>
                        ) : (
                          <div className="risk-list">
                            {redFlags.map((flag) => {
                              const confidence = getConfidence(flag);

                              return (
                                <article
                                  className="risk-card"
                                  key={flag.id}
                                >
                                  <div className="risk-card-top">
                                    <span className={riskClass(flag.severity)}>
                                      {flag.severity} risk
                                    </span>

                                    <span className="confidence">
                                      {confidence
                                        ? `${confidence}% evidence confidence`
                                        : "Reprocess required"}
                                    </span>
                                  </div>

                                  <h3>{flag.title}</h3>
                                  <p>{flag.explanation}</p>

                                  <div className="risk-detail">
                                    <span>Matched signal</span>
                                    <strong>
                                      {flag.matched_signals ||
                                        "Direct risk disclosure"}
                                    </strong>
                                  </div>

                                  <div className="confidence-note">
                                    {flag.confidence_explanation ||
                                      "This report was processed before confidence scoring. Reprocess it to calculate confidence."}
                                  </div>

                                  <a
                                    href={`${API_URL}/documents/${selectedDocument.id}/file#page=${flag.source_page}`}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    Source page {flag.source_page} →
                                  </a>

                                  <blockquote>{flag.evidence}</blockquote>
                                </article>
                              );
                            })}
                          </div>
                        )}
                      </section>
                    </section>
                  </>
                )}
              </section>
            )}

            {activeView === "research" && (
              <section className="research-layout">
                <section className="content-card research-main">
                  <div className="card-heading">
                    <div>
                      <p className="section-label">RESEARCH AGENT</p>
                      <h2>Ask about your annual reports</h2>
                      <p className="muted">
                        Answers are grounded only in your selected reports and
                        include source citations.
                      </p>
                    </div>

                    <span className="selection-count">
                      {selectedReports.length} reports selected
                    </span>
                  </div>

                  <div className="prompt-chips">
                    <button
                      onClick={() =>
                        setQuestion(
                          "What does the annual report say about debt and liquidity risk?"
                        )
                      }
                    >
                      Debt and liquidity risk
                    </button>
                    <button
                      onClick={() =>
                        setQuestion(
                          "Summarize revenue performance and profitability."
                        )
                      }
                    >
                      Revenue and profitability
                    </button>
                    <button
                      onClick={() =>
                        setQuestion(
                          "What red flags or financial risks are disclosed?"
                        )
                      }
                    >
                      Key risks and red flags
                    </button>
                  </div>

                  <div className="chat-window">
                    {chatMessages.length === 0 ? (
                      <div className="chat-empty">
                        <div className="empty-icon">◌</div>
                        <h3>Start a financial research conversation</h3>
                        <p>
                          Ask multi-part questions about selected annual
                          reports. The Research Agent retrieves relevant PDF
                          evidence before responding.
                        </p>
                      </div>
                    ) : (
                      chatMessages.map((chat, index) => (
                        <article
                          className={`message-bubble ${chat.role}`}
                          key={index}
                        >
                          <span className="message-author">
                            {chat.role === "user" ? "You" : "Research Agent"}
                          </span>

                          <p>{chat.content}</p>

                          {chat.role === "assistant" &&
                            chat.metrics?.length > 0 && (
                              <div className="mini-metrics">
                                {chat.metrics.map((metric, metricIndex) => (
                                  <div key={metricIndex}>
                                    <span>{metric.name}</span>
                                    <strong>{metric.value}</strong>
                                    <small>Page {metric.source_page}</small>
                                  </div>
                                ))}
                              </div>
                            )}

                          {chat.role === "assistant" &&
                            chat.reasoningSteps?.length > 0 && (
                              <details>
                                <summary>Evidence retrieval steps</summary>
                                <ol>
                                  {chat.reasoningSteps.map(
                                    (step, stepIndex) => (
                                      <li key={stepIndex}>{step}</li>
                                    )
                                  )}
                                </ol>
                              </details>
                            )}

                          {chat.role === "assistant" &&
                            chat.citations?.length > 0 && (
                              <div className="citation-group">
                                <strong>Source evidence</strong>

                                {chat.citations.map(
                                  (citation, citationIndex) => (
                                    <div
                                      className="citation-card"
                                      key={citationIndex}
                                    >
                                      <b>
                                        {citation.document_name ||
                                          `Document ${citation.document_id}`}{" "}
                                        · Page {citation.page}
                                      </b>
                                      <p>{citation.excerpt}</p>
                                    </div>
                                  )
                                )}
                              </div>
                            )}
                        </article>
                      ))
                    )}
                  </div>

                  <form className="ask-form" onSubmit={askResearch}>
                    <input
                      value={question}
                      placeholder="Ask a financial research question..."
                      onChange={(event) => setQuestion(event.target.value)}
                    />

                    <button
                      className="button primary"
                      type="submit"
                      disabled={processing}
                    >
                      {processing ? "Researching..." : "Send →"}
                    </button>
                  </form>
                </section>

                <aside className="content-card report-selection">
                  <p className="section-label">RESEARCH SCOPE</p>
                  <h2>Selected Reports</h2>
                  <p className="muted">
                    Choose the reports used for retrieval and comparison.
                  </p>

                  <div className="selection-list">
                    {completedDocuments.map((document) => (
                      <label key={document.id}>
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(document.id)}
                          onChange={() => toggleSelectedDocument(document.id)}
                        />
                        <span>
                          <strong>
                            {document.company_name ||
                              document.original_filename}
                          </strong>
                          <small>
                            {document.fiscal_year || "Annual Report"}
                          </small>
                        </span>
                      </label>
                    ))}
                  </div>

                  <button
                    className="button secondary full-width"
                    disabled={processing || selectedIds.length < 2}
                    onClick={compareReports}
                  >
                    Compare Selected Reports
                  </button>
                </aside>
              </section>
            )}

            {activeView === "comparison" && (
              <section className="content-card">
                <div className="card-heading">
                  <div>
                    <p className="section-label">COMPARISON AGENT</p>
                    <h2>Peer Benchmarking</h2>
                    <p className="muted">
                      Select at least two completed reports to generate a
                      side-by-side financial comparison.
                    </p>
                  </div>

                  <button
                    className="button primary"
                    disabled={processing || selectedIds.length < 2}
                    onClick={compareReports}
                  >
                    {processing ? "Comparing..." : "Run Comparison"}
                  </button>
                </div>

                {!comparison ? (
                  <div className="empty-state">
                    <div className="empty-icon">⇄</div>
                    <h3>No comparison generated yet</h3>
                    <p>
                      Select two or more reports from the Dashboard or
                      Research Chat, then run the Comparison Agent.
                    </p>
                  </div>
                ) : (
                  <div className="comparison-table-wrap">
                    <table className="comparison-table">
                      <thead>
                        <tr>
                          <th>Financial Metric</th>
                          {comparison.documents.map((document) => (
                            <th key={document.id}>
                              {document.company_name}
                              <small>
                                {document.fiscal_year || "Annual Report"}
                              </small>
                            </th>
                          ))}
                        </tr>
                      </thead>

                      <tbody>
                        {comparison.rows.map((row) => (
                          <tr key={row.metric_name}>
                            <td>
                              <strong>{row.metric_name}</strong>
                            </td>

                            {row.values.map((value) => (
                              <td key={value.document_id}>
                                <strong>{value.value}</strong>
                                {value.source_page && (
                                  <small>Source page {value.source_page}</small>
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            )}

            {activeView === "report" && (
              <section className="content-card">
                <div className="card-heading">
                  <div>
                    <p className="section-label">REPORT AGENT</p>
                    <h2>Analyst-Style Research Report</h2>
                    <p className="muted">
                      Executive summary, key financials, and risk findings for
                      the selected annual report.
                    </p>
                  </div>

                  <div className="report-actions">
                    <button
                      className="button primary"
                      disabled={!selectedDocument || processing}
                      onClick={generateReport}
                    >
                      Generate Report
                    </button>

                    {selectedDocument && (
                      <a
                        className="button secondary"
                        href={`${API_URL}/analysis/report/${selectedDocument.id}/pdf`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download PDF
                      </a>
                    )}
                  </div>
                </div>

                {!report ? (
                  <div className="empty-state">
                    <div className="empty-icon">▤</div>
                    <h3>No report summary generated</h3>
                    <p>
                      Open an annual report in the Report Workspace, then
                      generate an analyst-style summary.
                    </p>
                  </div>
                ) : (
                  <div className="report-output">
                    <section className="executive-summary">
                      <p className="section-label">EXECUTIVE SUMMARY</p>
                      <p>{report.executive_summary}</p>
                    </section>

                    <section>
                      <p className="section-label">KEY FINANCIALS</p>
                      <div className="metric-grid">
                        {report.key_financials?.map((metric, index) => (
                          <article className="metric-card" key={index}>
                            <span>{metric.metric_name}</span>
                            <strong>{metric.metric_value}</strong>
                            <small>
                              {metric.period || "Annual Report"} · Page{" "}
                              {metric.source_page}
                            </small>
                          </article>
                        ))}
                      </div>
                    </section>
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </main>

      {showUpload && (
        <div className="modal-overlay">
          <section className="modal">
            <button
              className="modal-close"
              onClick={() => setShowUpload(false)}
            >
              ×
            </button>

            <p className="section-label">DOCUMENT AGENT</p>
            <h2>Upload Annual Report</h2>
            <p className="muted">
              The system validates the PDF before analysis. Upload an Annual
              Report, Form 10-K, Form 20-F, or annual financial report.
            </p>

            <form className="upload-form" onSubmit={uploadDocument}>
              <label>
                Company Name
                <input
                  value={companyName}
                  placeholder="Example: Tesla, Inc."
                  onChange={(event) => setCompanyName(event.target.value)}
                />
              </label>

              <label>
                Fiscal Year
                <input
                  value={fiscalYear}
                  placeholder="Example: FY 2024"
                  onChange={(event) => setFiscalYear(event.target.value)}
                />
              </label>

              <label className="file-upload">
                <span>Choose annual-report PDF</span>
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={(event) =>
                    setPdfFile(event.target.files?.[0] || null)
                  }
                />
                <small>
                  {pdfFile
                    ? pdfFile.name
                    : "Maximum file size follows backend configuration"}
                </small>
              </label>

              <button
                className="button primary full-width"
                type="submit"
                disabled={processing}
              >
                {processing ? "Analysing Report..." : "Upload and Analyse"}
              </button>
            </form>
          </section>
        </div>
      )}

      {showSessionForm && (
        <div className="modal-overlay">
          <section className="modal small-modal">
            <button
              className="modal-close"
              onClick={() => setShowSessionForm(false)}
            >
              ×
            </button>

            <p className="section-label">NEW WORKSPACE</p>
            <h2>Create Research Workspace</h2>

            <form className="upload-form" onSubmit={createSession}>
              <label>
                Workspace Name
                <input
                  value={sessionName}
                  placeholder="Example: Electric Vehicle Sector Analysis"
                  onChange={(event) => setSessionName(event.target.value)}
                />
              </label>

              <button
                className="button primary full-width"
                type="submit"
                disabled={processing}
              >
                Create Workspace
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
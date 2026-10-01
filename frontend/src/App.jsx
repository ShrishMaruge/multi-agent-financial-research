import { useEffect, useMemo, useState } from "react";

const API_URL = "http://127.0.0.1:8000/api";
const GROUPS = [
  { title: "Income Statement", names: ["Revenue", "Cost of Revenue", "Gross Profit", "Operating Income", "Net Income", "Basic EPS", "Diluted EPS"] },
  { title: "Balance Sheet", names: ["Cash and Cash Equivalents", "Accounts Receivable", "Inventory", "Total Assets", "Total Liabilities", "Shareholders Equity", "Long Term Debt"] },
  { title: "Cash Flow", names: ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow"] }
];

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try { detail = (await response.json()).detail || detail; } catch { /* fallback */ }
    throw new Error(detail);
  }
  return response.json();
}

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [sessionName, setSessionName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [fiscalYear, setFiscalYear] = useState("");
  const [pdfFile, setPdfFile] = useState(null);
  const [message, setMessage] = useState("");
  const [processing, setProcessing] = useState(false);

  useEffect(() => { loadSessions(); }, []);

  const groupedMetrics = useMemo(() => {
    const used = new Set();
    const grouped = GROUPS.map((group) => {
      const values = metrics.filter((metric) => {
        if (!group.names.includes(metric.metric_name)) return false;
        used.add(metric.metric_name);
        return true;
      });
      return { title: group.title, values };
    }).filter((group) => group.values.length > 0);
    const others = metrics.filter((metric) => !used.has(metric.metric_name));
    if (others.length) grouped.push({ title: "Other Extracted Values", values: others });
    return grouped;
  }, [metrics]);

  async function loadSessions() {
    try { setSessions(await api("/sessions")); }
    catch (error) { setMessage(error.message); }
  }

  async function loadDocuments(sessionId) {
    try { setDocuments(await api(`/documents/session/${sessionId}`)); }
    catch (error) { setDocuments([]); setMessage(error.message); }
  }

  async function createSession(event) {
    event.preventDefault();
    if (!sessionName.trim()) return setMessage("Enter a research session name.");
    try {
      const session = await api("/sessions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: sessionName, description: "Annual report analysis" })
      });
      setSessionName(""); setSelectedSession(session); setSelectedDocument(null); setDocuments([]); setMetrics([]);
      await loadSessions(); setMessage("Session created. Upload an annual report.");
    } catch (error) { setMessage(error.message); }
  }

  async function selectSession(session) {
    setSelectedSession(session); setSelectedDocument(null); setMetrics([]); setMessage("");
    await loadDocuments(session.id);
  }

  async function selectDocument(document) {
    setSelectedDocument(document); setMetrics([]);
    try {
      const result = await api(`/documents/${document.id}/metrics`);
      setMetrics(result); setMessage(`${result.length} financial metrics loaded.`);
    } catch (error) { setMessage(error.message); }
  }

  async function uploadDocument(event) {
    event.preventDefault();
    if (!selectedSession || !pdfFile) return setMessage("Select a session and annual report PDF first.");
    try {
      setProcessing(true); setMessage("Document Agent and Extraction Agent are processing the report...");
      const formData = new FormData();
      formData.append("session_id", selectedSession.id); formData.append("company_name", companyName);
      formData.append("fiscal_year", fiscalYear); formData.append("file", pdfFile);
      const document = await api("/documents/upload", { method: "POST", body: formData });
      setCompanyName(""); setFiscalYear(""); setPdfFile(null);
      await loadDocuments(selectedSession.id); await selectDocument(document);
    } catch (error) { setMessage(`Upload failed: ${error.message}`); }
    finally { setProcessing(false); }
  }

  async function reprocessDocument() {
    if (!selectedDocument) return;
    try {
      setProcessing(true); setMessage("Reprocessing annual report...");
      const document = await api(`/documents/${selectedDocument.id}/reprocess`, { method: "POST" });
      await loadDocuments(selectedSession.id); await selectDocument(document);
    } catch (error) { setMessage(`Reprocessing failed: ${error.message}`); }
    finally { setProcessing(false); }
  }

  return <main className="app">
    <header className="hero"><h1>Multi-Agent Financial Research System</h1><p>Milestone 2: document processing and source-cited financial extraction.</p></header>
    <section className="panel"><h2>Research Session</h2>
      <form className="form-row" onSubmit={createSession}><input value={sessionName} placeholder="Example: Apple Annual Report Analysis" onChange={(event) => setSessionName(event.target.value)} /><button type="submit">Create Session</button></form>
      <div className="sessions">{sessions.map((session) => <button type="button" key={session.id} className={selectedSession?.id === session.id ? "session active" : "session"} onClick={() => selectSession(session)}>{session.name}</button>)}</div>
    </section>
    {selectedSession && <>
      <section className="panel"><h2>Upload Annual Report</h2>
        <form className="form-row" onSubmit={uploadDocument}><input value={companyName} placeholder="Company name" onChange={(event) => setCompanyName(event.target.value)} /><input value={fiscalYear} placeholder="Financial year" onChange={(event) => setFiscalYear(event.target.value)} /><input type="file" accept=".pdf,application/pdf" onChange={(event) => setPdfFile(event.target.files[0])} /><button type="submit" disabled={processing}>{processing ? "Processing..." : "Upload PDF"}</button></form>
        {message && <p className="message">{message}</p>}
      </section>
      <section className="panel"><div className="section-title"><h2>Uploaded Annual Reports</h2><button type="button" onClick={() => loadDocuments(selectedSession.id)}>Refresh</button></div>
        {documents.length === 0 ? <p>No annual reports uploaded in this session.</p> : <div className="scroll"><table><thead><tr><th>Document</th><th>Company</th><th>Year</th><th>Status</th><th>Pages</th><th>Chunks</th><th>Action</th></tr></thead><tbody>{documents.map((document) => <tr key={document.id}><td>{document.original_filename}</td><td>{document.company_name || "-"}</td><td>{document.fiscal_year || "-"}</td><td>{document.status}</td><td>{document.page_count}</td><td>{document.chunk_count}</td><td><button type="button" onClick={() => selectDocument(document)}>View Analysis</button></td></tr>)}</tbody></table></div>}
      </section>
      {selectedDocument && <section className="analysis"><section className="panel pdf"><div className="section-title"><h2>Original Annual Report</h2><button type="button" onClick={reprocessDocument} disabled={processing}>Reprocess</button></div><iframe title="Annual report PDF" src={`${API_URL}/documents/${selectedDocument.id}/file`} /></section><section className="panel"><h2>Extracted Financial Output</h2>{metrics.length === 0 && <p>No financial metrics were extracted from this report.</p>}{groupedMetrics.map((group) => <div className="metric-group" key={group.title}><h3>{group.title}</h3><div className="metric-grid">{group.values.map((metric) => <article className="metric-card" key={metric.id}><span>{metric.metric_name}</span><strong>{metric.metric_value}</strong><small>{metric.period || "Annual report period"}</small><a href={`${API_URL}/documents/${selectedDocument.id}/file#page=${metric.source_page}`} target="_blank" rel="noreferrer">Source Page {metric.source_page}</a></article>)}</div></div>)}</section></section>}
    </>}
  </main>;
}

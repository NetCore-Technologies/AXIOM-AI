import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BrainCircuit,
  Check,
  ChevronDown,
  CircleGauge,
  Cpu,
  Database,
  FlaskConical,
  FolderKanban,
  Gauge,
  HardDrive,
  Hammer,
  LayoutDashboard,
  ListFilter,
  Logs,
  Moon,
  Network,
  Play,
  Plus,
  RadioTower,
  Rocket,
  Search,
  ServerCog,
  Settings,
  ShieldCheck,
  Sparkles,
  Sun,
  TerminalSquare,
  TimerReset,
  Wrench,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Page =
  | "dashboard"
  | "models"
  | "datasets"
  | "training"
  | "evaluation"
  | "runtime"
  | "mcp"
  | "diagnostics"
  | "logs"
  | "settings";

type Theme = "dark" | "light";

const nav: Array<{ id: Page; label: string; icon: React.ElementType; section?: string }> = [
  { id: "dashboard", label: "Control Center", icon: LayoutDashboard, section: "WORKSPACE" },
  { id: "models", label: "Models", icon: BrainCircuit },
  { id: "datasets", label: "Datasets", icon: Database },
  { id: "training", label: "Training", icon: Hammer },
  { id: "evaluation", label: "Evaluation", icon: FlaskConical },
  { id: "runtime", label: "Runtime", icon: RadioTower, section: "OPERATIONS" },
  { id: "mcp", label: "MCP Inspector", icon: Network },
  { id: "diagnostics", label: "Diagnostics", icon: Wrench },
  { id: "logs", label: "Logs", icon: TerminalSquare },
  { id: "settings", label: "Settings", icon: Settings, section: "SYSTEM" },
];

const activity = [
  { time: "12:00", requests: 71 }, { time: "12:10", requests: 82 }, { time: "12:20", requests: 74 },
  { time: "12:30", requests: 97 }, { time: "12:40", requests: 88 }, { time: "12:50", requests: 111 },
  { time: "13:00", requests: 104 }, { time: "13:10", requests: 123 }, { time: "13:20", requests: 118 },
  { time: "13:30", requests: 134 }, { time: "13:40", requests: 126 }, { time: "13:50", requests: 143 },
  { time: "14:00", requests: 137 },
];

const latency = [72,70,68,73,69,67,65,66,62,60,61,58,57,55];

function App() {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("axiom-theme") as Theme) || "dark");
  const [booted, setBooted] = useState(() => localStorage.getItem("axiom-booted") === "1");
  const [setupDone, setSetupDone] = useState(() => localStorage.getItem("axiom-setup") === "1");
  const [page, setPage] = useState<Page>("dashboard");

  if (!booted) {
    return <Welcome theme={theme} onStart={() => { localStorage.setItem("axiom-booted", "1"); setBooted(true); }} />;
  }

  if (!setupDone) {
    return <Setup theme={theme} onComplete={() => { localStorage.setItem("axiom-setup", "1"); setSetupDone(true); }} />;
  }

  return (
    <div className={`app-shell ${theme}`}>
      <Sidebar page={page} setPage={setPage} />
      <main className="main-shell">
        <Topbar theme={theme} setTheme={(t) => { localStorage.setItem("axiom-theme", t); setTheme(t); }} page={page} />
        <div className="page-wrap">
          {page === "dashboard" && <Dashboard setPage={setPage} />}
          {page === "models" && <Models />}
          {page === "datasets" && <Datasets />}
          {page === "training" && <Training />}
          {page === "evaluation" && <Evaluation />}
          {page === "runtime" && <Runtime />}
          {page === "mcp" && <MCP />}
          {page === "diagnostics" && <Diagnostics />}
          {page === "logs" && <LogsPage />}
          {page === "settings" && <SettingsPage />}
        </div>
      </main>
    </div>
  );
}

function Welcome({ theme, onStart }: { theme: Theme; onStart: () => void }) {
  return (
    <div className={`onboarding ${theme}`}>
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <section className="onboarding-copy">
        <div>
          <div className="brand-lockup"><div className="brand-mark">A</div><div><b>AXIOM</b><span>AI ENGINEERING PLATFORM</span></div></div>
          <div className="step-strip"><span className="active">01</span><span>02</span><span>03</span></div>
        </div>
        <div className="hero-block">
          <div className="eyebrow"><Sparkles size={14} /> BUILD AI. OWN AI.</div>
          <h1>Welcome to<br /><span>AXIOM.</span></h1>
          <p>Build, inspect, train and operate your AI stack from one local-first engineering control center.</p>
          <button className="primary-button" onClick={onStart}>Enter AXIOM <ArrowRight size={18} /></button>
        </div>
        <div className="principles">
          <InfoLine icon={ShieldCheck} title="LOCAL-FIRST" text="Your workspace stays under your control." />
          <InfoLine icon={BrainCircuit} title="AI ENGINEERING" text="Models, data, training and runtime in one flow." />
          <InfoLine icon={Activity} title="FULL VISIBILITY" text="Inspect requests, logs, metrics and failures." />
        </div>
        <div className="tiny-footer">AXIOM • BUILD AI. OWN AI.</div>
      </section>
      <section className="onboarding-preview">
        <div className="preview-window">
          <div className="preview-bar"><div className="traffic"><i /><i /><i /></div><span>AXIOM / CONTROL CENTER</span><b><span className="pulse" /> LIVE</b></div>
          <div className="preview-grid">
            <div className="glass-card highlight"><small>SYSTEM HEALTH</small><strong>98.7<span>%</span></strong><Sparkline values={activity.map((d) => d.requests)} /></div>
            <div className="glass-card"><small>ACTIVE MODEL</small><b className="hero-small">Qwen 3 • 8B</b><em>READY</em></div>
            <div className="glass-card"><small>REQUESTS / MIN</small><b className="hero-small">1,284</b><span className="delta">+14.2%</span></div>
            <div className="glass-card wide"><small>INFERENCE LATENCY</small><Sparkline values={latency} /></div>
          </div>
        </div>
      </section>
    </div>
  );
}

function InfoLine({ icon: Icon, title, text }: { icon: React.ElementType; title: string; text: string }) {
  return <div className="info-line"><Icon size={16} /><div><b>{title}</b><span>{text}</span></div></div>;
}

function Setup({ theme, onComplete }: { theme: Theme; onComplete: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [reveal, setReveal] = useState(false);
  const req = useMemo(() => ({
    username: username.length >= 3,
    length: password.length >= 8,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    match: password.length > 0 && password === confirm,
  }), [username, password, confirm]);
  const canContinue = req.username && req.length && req.upper && req.lower && req.number && req.match;

  return <div className={`onboarding centered ${theme}`}>
    <div className="setup-panel">
      <div className="setup-head"><div className="brand-mark">A</div><div><b>AXIOM</b><span>ADMINISTRATOR SETUP</span></div></div>
      <div className="step-strip compact"><span className="active">01</span><span>02</span><span>03</span></div>
      <div className="eyebrow">STEP 1 OF 3 • ADMINISTRATOR</div>
      <h1>Create your <span>AXIOM account.</span></h1>
      <p>This local administrator account protects access to your AXIOM workspace and control center.</p>
      <Field label="Username" valid={req.username} hint="3+ character username"><input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="administrator" /></Field>
      <Field label="Password" valid={req.length && req.upper && req.lower && req.number} action={<button className="show-button" onClick={() => setReveal(!reveal)}>{reveal ? "Hide" : "Show"}</button>}><input type={reveal ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a secure password" autoComplete="new-password" /></Field>
      <div className="requirements"><Requirement ok={req.length} label="8+ character password" /><Requirement ok={req.upper && req.lower} label="Upper + lowercase" /><Requirement ok={req.number} label="Contains a number" /></div>
      <Field label="Confirm password" valid={req.match} hint={req.match ? "Passwords match" : "Passwords must match"}><input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Repeat your password" autoComplete="new-password" /></Field>
      <button className="primary-button full" disabled={!canContinue} onClick={onComplete}>Continue <ArrowRight size={18} /></button>
      <div className="secure-note"><ShieldCheck size={14} /> Stored locally by the AXIOM installation.</div>
    </div>
  </div>;
}

function Field({ label, valid, hint, action, children }: { label: string; valid: boolean; hint?: string; action?: React.ReactNode; children: React.ReactNode }) {
  return <div className="field"><label>{label}</label><div className={`input-shell ${valid ? "valid" : ""}`}>{children}{valid && <Check size={17} />}{action}</div>{hint && <small className={valid && label === "Confirm password" ? "valid-text" : ""}>{hint}</small>}</div>;
}

function Requirement({ ok, label }: { ok: boolean; label: string }) {
  return <div className={`requirement ${ok ? "ok" : ""}`}><span>{ok ? <Check size={11} /> : ""}</span>{label}</div>;
}

function Sidebar({ page, setPage }: { page: Page; setPage: (p: Page) => void }) {
  return <aside className="sidebar">
    <div className="sidebar-brand"><div className="brand-mark small">A</div><div><b>AXIOM</b><span>CONTROL CENTER</span></div></div>
    <div className="workspace-card"><div className="avatar">A</div><div><b>Local Workspace</b><span>Development</span></div><ChevronDown size={14} /></div>
    <nav>{nav.map((item) => <div key={item.id}>{item.section && <div className="nav-section">{item.section}</div>}<button onClick={() => setPage(item.id)} className={`nav-item ${page === item.id ? "active" : ""}`}><item.icon size={17} /><span>{item.label}</span>{item.id === "diagnostics" && <em>2</em>}</button></div>)}</nav>
    <div className="sidebar-bottom"><div className="core-state"><span><i className="pulse" /> AXIOM CORE</span><b>ONLINE</b></div><small>AXIOM • BUILD AI. OWN AI.</small></div>
  </aside>;
}

function Topbar({ theme, setTheme, page }: { theme: Theme; setTheme: (t: Theme) => void; page: Page }) {
  const title = nav.find((n) => n.id === page)?.label ?? "Control Center";
  return <header className="topbar"><div className="breadcrumb">AXIOM <span>/</span> {title}</div><div className="top-actions"><div className="search"><Search size={15} /><input placeholder="Search AXIOM..." /></div><button className="icon-button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}</button><div className="profile"><span>A</span><b>Administrator</b></div></div></header>;
}

function Dashboard({ setPage }: { setPage: (p: Page) => void }) {
  return <>
    <div className="page-heading"><div><div className="eyebrow">CONTROL CENTER • LOCAL ENGINE</div><h2>Good morning. <span>AXIOM is ready.</span></h2><p>Your AI stack is healthy and waiting for the next build.</p></div><button className="secondary-button" onClick={() => setPage("diagnostics")}><CircleGauge size={16} /> Run diagnostics</button></div>
    <div className="metric-grid"><MetricCard icon={Gauge} title="System Health" value="98.7%" delta="+1.8%" /><MetricCard icon={Activity} title="Requests / min" value="1,284" delta="+14.2%" /><MetricCard icon={TimerReset} title="Avg. latency" value="54 ms" delta="-8.4%" /><MetricCard icon={Cpu} title="Runtime load" value="64%" delta="12 GB / 24 GB" /></div>
    <div className="dashboard-grid">
      <Panel title="Inference activity" action="LIVE" wide><div className="chart-legend"><span><i className="dot cyan" /> Requests</span><span><i className="dot muted" /> Baseline</span></div><div className="chart-large"><ResponsiveContainer width="100%" height="100%"><AreaChart data={activity}><defs><linearGradient id="axiomArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#37dfd1" stopOpacity={0.25} /><stop offset="100%" stopColor="#37dfd1" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="rgba(255,255,255,.05)" vertical={false} /><XAxis dataKey="time" tick={{ fill: "#546a6c", fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis hide domain={[40, 160]} /><Tooltip contentStyle={{ background: "#0b191c", border: "1px solid rgba(100,240,225,.18)", borderRadius: 10, fontSize: 10 }} /><Area type="monotone" dataKey="requests" stroke="#39dfd0" strokeWidth={2.4} fill="url(#axiomArea)" /></AreaChart></ResponsiveContainer></div></Panel>
      <Panel title="Runtime health" action="ALL SYSTEMS"><div className="health-list"><HealthRow icon={ServerCog} label="AXIOM Core" value="Operational" /><HealthRow icon={BrainCircuit} label="Inference Engine" value="Ready" /><HealthRow icon={FolderKanban} label="Model Registry" value="Synced" /><HealthRow icon={Network} label="MCP Gateway" value="3 / 3 online" /></div></Panel>
      <Panel title="Recent activity" action="VIEW LOGS"><TimelineItem time="14:02:18" title="Qwen 3 evaluation completed" detail="42 / 42 checks passed" good /><TimelineItem time="13:58:44" title="MCP request completed" detail="tools.list • 182 ms" /><TimelineItem time="13:51:09" title="Dataset validation" detail="train.jsonl • 5 valid / 1 invalid" warn /><TimelineItem time="13:40:31" title="Runtime health check" detail="No blocking issues" good /></Panel>
      <Panel title="AI stack" action="MANAGE"><div className="stack-grid"><StackCard icon={BrainCircuit} title="Qwen 3 • 8B" sub="Local model" state="READY" /><StackCard icon={Database} title="train.jsonl" sub="4 clean samples" state="CLEAN" /><StackCard icon={Zap} title="LoRA profile" sub="rank 8 • seq 1024" state="READY" /><StackCard icon={Cpu} title="CPU runtime" sub="Development mode" state="ACTIVE" /></div></Panel>
    </div>
  </>;
}

function MetricCard({ icon: Icon, title, value, delta }: { icon: React.ElementType; title: string; value: string; delta: string }) { return <div className="metric-card"><div className="metric-icon"><Icon size={17} /></div><small>{title}</small><strong>{value}</strong><span>{delta}</span></div>; }
function Panel({ title, action, children, wide = false }: { title: string; action?: string; children: React.ReactNode; wide?: boolean }) { return <section className={`panel ${wide ? "wide-panel" : ""}`}><div className="panel-head"><h3>{title}</h3>{action && <button>{action}</button>}</div>{children}</section>; }
function HealthRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) { return <div className="health-row"><div className="health-icon"><Icon size={15} /></div><div><b>{label}</b><span>{value}</span></div><i className="pulse" /></div>; }
function TimelineItem({ time, title, detail, good, warn }: { time: string; title: string; detail: string; good?: boolean; warn?: boolean }) { return <div className="timeline"><i className={warn ? "warn-pin" : good ? "good-pin" : "pin"} /><div><small>{time}</small><b>{title}</b><span>{detail}</span></div></div>; }
function StackCard({ icon: Icon, title, sub, state }: { icon: React.ElementType; title: string; sub: string; state: string }) { return <div className="stack-card"><div className="stack-icon"><Icon size={15} /></div><div><b>{title}</b><span>{sub}</span></div><em>{state}</em></div>; }
function FeaturePage({ kicker, title, desc, actions, children }: { kicker: string; title: string; desc: string; actions?: React.ReactNode; children: React.ReactNode }) { return <><div className="page-heading"><div><div className="eyebrow">{kicker}</div><h2>{title}</h2><p>{desc}</p></div>{actions}</div>{children}</>; }
function InfoCard({ icon: Icon, label, value, detail }: { icon: React.ElementType; label: string; value: string; detail: string }) { return <div className="info-card"><div><span>{label}</span><Icon size={16} /></div><b>{value}</b><small>{detail}</small></div>; }
function Models() { return <FeaturePage kicker="MODEL REGISTRY" title="Models" desc="Manage local models, metadata, versions, quantization and serving profiles." actions={<button className="primary-button"><Plus size={16} /> Add model</button>}><div className="info-grid"><InfoCard icon={BrainCircuit} label="Registered models" value="3" detail="1 ready • 2 metadata-only" /><InfoCard icon={HardDrive} label="Storage" value="18.4 GB" detail="62% of model volume" /><InfoCard icon={Sparkles} label="Active" value="Qwen 3 • 8B" detail="Transformers / local runtime" /></div><Panel title="Registry" action="REFRESH"><DataTable rows={[["Qwen 3 • 8B","safetensors","8B","FP16","READY"],["Qwen 3 • 8B Base","safetensors","8B","INT4","METADATA"],["Development model","transformers","0.14B","FP16","READY"]]} /></Panel></FeaturePage>; }
function Datasets() { return <FeaturePage kicker="DATA ENGINEERING" title="Datasets" desc="Inspect, clean, validate and trace the data feeding your models." actions={<button className="primary-button"><Plus size={16} /> Import dataset</button>}><div className="info-grid"><InfoCard icon={Check} label="Clean samples" value="4" detail="Latest validation" /><InfoCard icon={AlertTriangle} label="Invalid" value="1" detail="Needs attention" /><InfoCard icon={BarChart3} label="Est. tokens" value="76" detail="Current training set" /></div><Panel title="Latest inspection" action="OPEN REPORT"><DataTable rows={[["Total samples","6","","","INFO"],["Valid","5","","","PASS"],["Invalid","1","","","WARN"],["Duplicates","1","","","WARN"],["Detected fields","instruction, output","","","PASS"]]} /></Panel></FeaturePage>; }
function Training() { return <FeaturePage kicker="MODEL OPTIMIZATION" title="Training" desc="Build reproducible fine-tuning runs with hardware-aware configurations." actions={<button className="primary-button"><Play size={16} /> New run</button>}><div className="info-grid"><InfoCard icon={Zap} label="Recommended" value="LoRA" detail="Rank 8 • batch 1 • grad 16" /><InfoCard icon={BarChart3} label="Sequence length" value="1024" detail="CPU development profile" /><InfoCard icon={Cpu} label="Hardware" value="CPU" detail="No GPU detected" /></div><Panel title="Training plan" action="EDIT"><div className="plan-grid"><Plan label="Base model" value="Qwen 3 • 8B" /><Plan label="Dataset" value="train.cleaned.jsonl" /><Plan label="Method" value="LoRA" /><Plan label="Epochs" value="1" /><Plan label="Batch" value="1 × 16 accumulation" /><Plan label="Deployment" value="Local" /></div></Panel></FeaturePage>; }
function Evaluation() { return <FeaturePage kicker="QUALITY GATES" title="Evaluation" desc="Turn model quality into a repeatable engineering signal." actions={<button className="primary-button"><Play size={16} /> Run evaluation</button>}><div className="info-grid"><InfoCard icon={Gauge} label="Latest score" value="94.2" detail="42 assertions • 39 pass" /><InfoCard icon={BarChart3} label="Regression delta" value="+3.6" detail="Against previous run" /><InfoCard icon={AlertTriangle} label="Failures" value="3" detail="2 warning • 1 blocking" /></div><Panel title="Quality trend"><div className="chart-large"><ResponsiveContainer width="100%" height="100%"><AreaChart data={[65,68,72,70,74,78,77,81,80,85,83,87,89,86,90,91,92,94,93,94,95].map((score, i) => ({ i, score }))}><CartesianGrid stroke="rgba(255,255,255,.05)" vertical={false} /><XAxis dataKey="i" hide /><YAxis hide domain={[55,100]} /><Area type="monotone" dataKey="score" stroke="#39dfd0" fill="rgba(57,223,208,.08)" strokeWidth={2.3} /></AreaChart></ResponsiveContainer></div></Panel></FeaturePage>; }
function Runtime() { return <FeaturePage kicker="LOCAL RUNTIME" title="Runtime" desc="Inspect model serving, resource usage, request flow and deployment state." actions={<button className="secondary-button"><Rocket size={16} /> Deploy profile</button>}><div className="info-grid"><InfoCard icon={RadioTower} label="Status" value="READY" detail="Local inference enabled" /><InfoCard icon={Activity} label="Requests" value="1,284" detail="This minute" /><InfoCard icon={Cpu} label="Memory" value="12 / 24 GB" detail="50% allocated" /></div><Panel title="Request throughput" action="LAST 30 MIN"><div className="chart-large"><ResponsiveContainer width="100%" height="100%"><AreaChart data={activity}><CartesianGrid stroke="rgba(255,255,255,.05)" vertical={false} /><XAxis dataKey="time" tick={{ fill: "#546a6c", fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis hide /><Area type="monotone" dataKey="requests" stroke="#39dfd0" fill="rgba(57,223,208,.08)" strokeWidth={2.3} /></AreaChart></ResponsiveContainer></div></Panel></FeaturePage>; }
function MCP() { return <FeaturePage kicker="MODEL CONTEXT PROTOCOL" title="MCP Inspector" desc="Inspect tools, resources, prompts, schemas and live execution requests." actions={<button className="primary-button"><Plus size={16} /> Add server</button>}><div className="mcp-layout"><div className="mcp-servers">{["filesystem","local-runtime","developer-tools"].map((name, i) => <button className={`server-row ${i === 0 ? "active" : ""}`} key={name}><div className="server-icon"><Network size={15} /></div><div><b>{name}</b><span>{i === 1 ? "Runtime" : "stdio"} • {i + 1} tools</span></div><i className="pulse" /></button>)}</div><Panel title="filesystem • tools" action="CONNECTED"><DataTable rows={[["read_file","valid","182 ms","","200"],["write_file","valid","203 ms","","200"],["list_directory","valid","92 ms","","200"],["search_files","valid","118 ms","","204"]]} /></Panel></div></FeaturePage>; }
function Diagnostics() { return <FeaturePage kicker="OBSERVABILITY" title="Diagnostics" desc="One screen for health checks, bottlenecks, configuration drift and blockers." actions={<button className="primary-button"><Wrench size={16} /> Run full scan</button>}><div className="diagnostic-score"><div><small>OVERALL HEALTH</small><strong>98.7</strong><span>/ 100</span></div><div className="score-ring">98%</div></div><div className="diag-list"><Diagnostic title="Core services" detail="All required AXIOM services are responding." good /><Diagnostic title="Model environment" detail="Qwen metadata is available. Full weights are not present locally." warn /><Diagnostic title="Dataset integrity" detail="1 invalid record and 1 duplicate detected in latest inspection." warn /><Diagnostic title="Hardware fit" detail="CPU development profile is valid for lightweight runs." good /></div></FeaturePage>; }
function Diagnostic({ title, detail, good, warn }: { title: string; detail: string; good?: boolean; warn?: boolean }) { return <div className="diag-row"><div className={`diag-icon ${warn ? "warn" : ""}`}>{warn ? <AlertTriangle size={16} /> : <Check size={16} />}</div><div><b>{title}</b><span>{detail}</span></div><em>{good ? "PASS" : "REVIEW"}</em></div>; }
function LogsPage() { return <FeaturePage kicker="EVENT STREAM" title="Logs" desc="Trace what AXIOM is doing, not just whether it is running." actions={<button className="secondary-button"><ListFilter size={16} /> Filter</button>}><Panel title="Live event stream" action="STREAMING"><div className="log-list">{[["14:02:18.342","INFO","runtime.inference","Request completed","182ms • tokens=143"],["14:02:17.901","INFO","mcp.filesystem","tools.list","3 tools exposed"],["14:01:59.221","WARN","dataset.inspect","Invalid sample","row=6"],["13:58:44.018","INFO","evaluation.run","Suite complete","42 checks • 39 pass"],["13:55:22.704","INFO","axiom.core","Health check","all services ready"]].map((r) => <div className="log-row" key={r.join("-")}><span>{r[0]}</span><b className={r[1] === "WARN" ? "warn-text" : ""}>{r[1]}</b><span>{r[2]}</span><span>{r[3]}</span><small>{r[4]}</small></div>)}</div></Panel></FeaturePage>; }
function SettingsPage() { return <FeaturePage kicker="SYSTEM" title="Settings" desc="Control the local AXIOM installation, runtime and workspace defaults."><Panel title="Workspace"><div className="plan-grid"><Plan label="Workspace" value="Local Workspace" /><Plan label="Deployment" value="Local" /><Plan label="Telemetry" value="Local only" /><Plan label="UI" value="AXIOM Control Center" /></div></Panel></FeaturePage>; }
function Plan({ label, value }: { label: string; value: string }) { return <div className="plan"><small>{label}</small><b>{value}</b></div>; }
function DataTable({ rows }: { rows: string[][] }) { return <div className="data-table"><div className="table-head"><span>ITEM</span><span>DETAIL</span><span>VALUE</span><span>STATE</span><span>RESULT</span></div>{rows.map((row, i) => <div className="table-row" key={i}>{row.map((cell, j) => <span className={j === row.length - 1 ? "status-text" : ""} key={j}>{cell}</span>)}</div>)}</div>; }
function Sparkline({ values }: { values: number[] }) { const max = Math.max(...values); const min = Math.min(...values); const pts = values.map((v, i) => `${(i / Math.max(1, values.length - 1)) * 100},${90 - ((v - min) / Math.max(1, max - min)) * 75}`).join(" "); return <svg className="sparkline" viewBox="0 0 100 100" preserveAspectRatio="none"><polyline points={pts} /></svg>; }

export default App;

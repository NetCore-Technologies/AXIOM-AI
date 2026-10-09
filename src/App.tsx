import AxiomOptimizer from "./components/AxiomOptimizer";
import AxiomQuantizer from "./components/AxiomQuantizer";
import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {

Activity,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BrainCircuit,
  Check,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  CircleGauge,
  Clock3,
  Command,
  Cpu,
  Database,
  FileCode2,
  Gauge,
  Hammer,
  HardDrive,
  KeyRound,
  LayoutDashboard,
  ListFilter,
  LockKeyhole,
  Menu,
  Moon,
  Network,
  PanelLeftClose,
  Play,
  Plus,
  RadioTower,
  RefreshCcw,
  Search,
  ServerCog,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  TerminalSquare,
  TimerReset,
  TriangleAlert,
  Wrench,
  X,
  Zap,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_AXIOM_API_URL || "";

function equalSecrets(a: string, b: string): boolean {
  const left = new TextEncoder().encode(a);
  const right = new TextEncoder().encode(b);

  if (left.length !== right.length) {
    return false;
  }

  let diff = 0;

  for (let i = 0; i < left.length; i += 1) {
    diff |= left[i] ^ right[i];
  }

  return diff === 0;
}


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
  | "settings"
  | "optimizer"
  | "quantizer";

type Theme = "dark" | "light";
type Tone = "success" | "warning" | "danger" | "neutral" | "info";

type NavItem = {
  id: Page;
  label: string;
  description: string;
  icon: LucideIcon;
  section?: string;
};

type Notice = {
  message: string;
  tone: Tone;
};

const navItems: NavItem[] = [  {
    id: "optimizer",
    label: "Agent Optimizer",
    description: "Interactive hardware-aware optimization",
    icon: Zap,
    section: "OPTIMIZATION",
  },
{
  id: "quantizer",
  label: "Quantization Lab",
  description: "Hardware-aware quantization and fit planning",
  icon: SlidersHorizontal,
},

  {
    id: "dashboard",
    label: "Control center",
    description: "Workspace overview",
    icon: LayoutDashboard,
    section: "WORKSPACE",
  },
  {
    id: "models",
    label: "Models",
    description: "Registry and metadata",
    icon: BrainCircuit,
  },
  {
    id: "datasets",
    label: "Datasets",
    description: "Inspect and validate data",
    icon: Database,
  },
  {
    id: "training",
    label: "Training",
    description: "Hardware-aware plans",
    icon: Hammer,
  },
  {
    id: "evaluation",
    label: "Evaluation",
    description: "Quality gates and reports",
    icon: CircleGauge,
  },
  {
    id: "runtime",
    label: "Runtime",
    description: "Local serving and requests",
    icon: RadioTower,
    section: "OPERATIONS",
  },
  {
    id: "mcp",
    label: "MCP inspector",
    description: "Tools and resources",
    icon: Network,
  },
  {
    id: "diagnostics",
    label: "Diagnostics",
    description: "Health and configuration",
    icon: Wrench,
  },
  {
    id: "logs",
    label: "Logs",
    description: "Runtime event stream",
    icon: TerminalSquare,
  },
  {
    id: "settings",
    label: "Settings",
    description: "Workspace and security",
    icon: Settings,
    section: "SYSTEM",
  },
];

const pageMeta: Record<
  Page,
  { label: string; kicker: string; description: string }
> = {
  optimizer: {
    label: "Agent Optimizer",
    kicker: "BETA 5 / MODEL OPTIMIZATION",
    description: "Interactive questionnaire, hardware detection and quantization planning.",
  },
  quantizer: {
    label: "Quantization Lab",
    kicker: "BETA 5 / HARDWARE OPTIMIZATION",
    description: "Choose an agent profile and hardware target to select a model quantization plan.",
  },
  dashboard: {
    label: "Control center",
    kicker: "CONTROL CENTER / LOCAL WORKSPACE",
    description: "A quiet place to see what is ready, what needs attention, and what is still disconnected.",
  },
  models: {
    label: "Models",
    kicker: "MODEL REGISTRY",
    description: "Inspect model metadata and keep local model decisions close to the rest of your stack.",
  },
  datasets: {
    label: "Datasets",
    kicker: "DATA ENGINEERING",
    description: "Validate, clean, and understand the data that feeds your experiments.",
  },
  training: {
    label: "Training",
    kicker: "MODEL OPTIMIZATION",
    description: "Shape a reproducible training plan around the hardware you actually have.",
  },
  evaluation: {
    label: "Evaluation",
    kicker: "QUALITY GATES",
    description: "Make model quality visible with repeatable checks instead of optimistic guesses.",
  },
  runtime: {
    label: "Runtime",
    kicker: "LOCAL RUNTIME",
    description: "See serving readiness and request flow once the local runtime is connected.",
  },
  mcp: {
    label: "MCP inspector",
    kicker: "MODEL CONTEXT PROTOCOL",
    description: "Inspect tools, resources, prompts, and schemas without losing the protocol context.",
  },
  diagnostics: {
    label: "Diagnostics",
    kicker: "OBSERVABILITY",
    description: "Find configuration drift and local blockers before they become confusing failures.",
  },
  logs: {
    label: "Logs",
    kicker: "EVENT STREAM",
    description: "Trace what the workspace is doing, not just whether it appears to be running.",
  },
  settings: {
    label: "Settings",
    kicker: "SYSTEM / PREFERENCES",
    description: "Tune the local interface and protect the administrator session.",
  },
};

const platformModules: Array<{
  page: Page;
  title: string;
  description: string;
  state: string;
  tone: Tone;
  icon: LucideIcon;
}> = [
  {
    page: "optimizer",
    title: "Agent Optimizer",
    description: "Questionnaire-driven model sizing, quantization and benchmark planning",
    state: "Beta 5",
    tone: "success",
    icon: Zap,
  },
  {
    page: "models",
    title: "Models",
    description: "Metadata, formats, parameters, quantization",
    state: "CLI surface",
    tone: "neutral",
    icon: BrainCircuit,
  },
  {
    page: "datasets",
    title: "Datasets",
    description: "JSONL inspection, validation, cleaning",
    state: "CLI surface",
    tone: "neutral",
    icon: Database,
  },
  {
    page: "training",
    title: "Training",
    description: "Hardware-aware planning and fit estimates",
    state: "Plan only",
    tone: "warning",
    icon: Hammer,
  },
  {
    page: "runtime",
    title: "Runtime",
    description: "Local inference and serving foundation",
    state: "Not connected",
    tone: "warning",
    icon: RadioTower,
  },
];

const activityBars = [38, 50, 46, 64, 58, 72, 68, 80, 74, 88, 82, 92, 86, 96, 90, 100];

type StoredAdminRecord = {
  version: 1;
  username: string;
  salt: string;
  iv: string;
  ciphertext: string;
  updatedAt: number;
};

const ADMIN_KEY = "axiom-admin-v2";
const LEGACY_ADMIN_KEY = "axiom-admin";
const SESSION_KEY = "axiom-session";
const THEME_KEY = "axiom-theme";

const ADMIN_VERIFIER = "AXIOM-ADMIN-VERIFIER-V1";

function encodeBase64(bytes: Uint8Array): string {
  let binary = "";

  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }

  return btoa(binary);
}

function decodeBase64(value: string): Uint8Array {
  return Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
}

async function derivePasswordKey(password: string, salt: Uint8Array): Promise<CryptoKey> {
  const baseKey = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(password),
    "PBKDF2",
    false,
    ["deriveKey"],
  );

  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: new Uint8Array(salt).buffer as ArrayBuffer,
      iterations: 310000,
      hash: "SHA-256",
    },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

async function encryptVerifier(password: string, salt: Uint8Array, iv: Uint8Array): Promise<string> {
  const key = await derivePasswordKey(password, salt);
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: new Uint8Array(iv) },
    key,
    new TextEncoder().encode(ADMIN_VERIFIER),
  );

  return encodeBase64(new Uint8Array(encrypted));
}

async function decryptVerifier(password: string, record: StoredAdminRecord): Promise<boolean> {
  try {
    const key = await derivePasswordKey(password, decodeBase64(record.salt));
    const decrypted = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: new Uint8Array(decodeBase64(record.iv)) },
      key,
      decodeBase64(record.ciphertext) as unknown as BufferSource,
    );

    return equalSecrets(new TextDecoder().decode(decrypted), ADMIN_VERIFIER);
  } catch {
    return false;
  }
}

function readAdmin(): StoredAdminRecord | null {
  const raw = localStorage.getItem(ADMIN_KEY);

  if (!raw) {
    localStorage.removeItem(LEGACY_ADMIN_KEY);
    return null;
  }

  try {
    const value: unknown = JSON.parse(raw);

    if (
      !value ||
      typeof value !== "object" ||
      (value as Partial<StoredAdminRecord>).version !== 1 ||
      typeof (value as Partial<StoredAdminRecord>).username !== "string" ||
      typeof (value as Partial<StoredAdminRecord>).salt !== "string" ||
      typeof (value as Partial<StoredAdminRecord>).iv !== "string" ||
      typeof (value as Partial<StoredAdminRecord>).ciphertext !== "string"
    ) {
      return null;
    }

    return value as StoredAdminRecord;
  } catch {
    return null;
  }
}

function getStoredTheme(): Theme {
  return localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
}

function isAuthenticated(): boolean {
  return sessionStorage.getItem(SESSION_KEY) === "1";
}

function getAdministratorName(): string {
  return readAdmin()?.username ?? "Administrator";
}

async function currentAdministrator(): Promise<string> {
  return getAdministratorName();
}


function getGreeting(): string {
  const hour = new Date().getHours();

  if (hour >= 5 && hour < 12) {
    return "Good morning";
  }

  if (hour >= 12 && hour < 18) {
    return "Good afternoon";
  }

  return "Good evening";
}

async function saveAdministrator(
  username: string,
  password: string,
): Promise<void> {
  const normalizedUsername = username.trim();

  if (normalizedUsername.length < 3 || password.length === 0) {
    throw new Error("Invalid administrator credentials.");
  }

  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await encryptVerifier(password, salt, iv);

  const record: StoredAdminRecord = {
    version: 1,
    username: normalizedUsername,
    salt: encodeBase64(salt),
    iv: encodeBase64(iv),
    ciphertext,
    updatedAt: Date.now(),
  };

  localStorage.setItem(
    ADMIN_KEY,
    JSON.stringify(record),
  );
  localStorage.removeItem(LEGACY_ADMIN_KEY);
}

async function verifyAdministrator(
  username: string,
  password: string,
): Promise<boolean> {
  const admin = readAdmin();

  if (!admin || admin.username !== username.trim()) {
    return false;
  }

  return decryptVerifier(password, admin);
}

function App() {

  const [theme, setTheme] = useState<Theme>(getStoredTheme);
  const [booted, setBooted] = useState(
    () => localStorage.getItem("axiom-booted") === "1",
  );
  const [setupDone, setSetupDone] = useState(
    () => localStorage.getItem("axiom-setup") === "1" && Boolean(localStorage.getItem(ADMIN_KEY)),
  );
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [page, setPage] = useState<Page>("dashboard");
  const [username, setUsername] = useState("Administrator");

  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  useEffect(() => {
    if (!notice) {
      return;
    }

    const timeout = window.setTimeout(() => setNotice(null), 4200);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  useEffect(() => {
    if (!authenticated) {
      return;
    }

    let timeout: number | undefined;
    const logoutForInactivity = () => {
      sessionStorage.removeItem(SESSION_KEY);
      setAuthenticated(false);
      setChangePasswordOpen(false);
      setNotice({ message: "Your session expired after 10 minutes of inactivity.", tone: "warning" });
    };
    const resetTimer = () => {
      if (timeout !== undefined) {
        window.clearTimeout(timeout);
      }

      timeout = window.setTimeout(logoutForInactivity, 10 * 60 * 1000);
    };
    const activityEvents = [
      "mousemove",
      "mousedown",
      "keydown",
      "touchstart",
      "scroll",
      "pointerdown",
    ];

    activityEvents.forEach((event) => window.addEventListener(event, resetTimer));
    resetTimer();

    return () => {
      if (timeout !== undefined) {
        window.clearTimeout(timeout);
      }

      activityEvents.forEach((event) => window.removeEventListener(event, resetTimer));
    };
  }, [authenticated]);

  useEffect(() => {
    if (!authenticated) {
      return;
    }

    currentAdministrator()
      .then(setUsername)
      .catch(() => setUsername("Administrator"));
  }, [authenticated]);

  const setAndPersistTheme = (nextTheme: Theme) => {
    localStorage.setItem(THEME_KEY, nextTheme);
    setTheme(nextTheme);
  };

  const notify = (message: string, tone: Tone = "info") => {
    setNotice({ message, tone });
  };

  const navigate = (nextPage: Page) => {
    setPage(nextPage);
    setMobileNavOpen(false);
  };

  if (!booted) {
    return (
      <Welcome
        theme={theme}
        setTheme={setAndPersistTheme}
        onStart={() => {
          localStorage.setItem("axiom-booted", "1");
          setBooted(true);
        }}
      />
    );
  }

  if (!setupDone) {
    return (
      <Setup
        theme={theme}
        setTheme={setAndPersistTheme}
        onComplete={async (username, password) => {
          await saveAdministrator(username, password);
          localStorage.setItem("axiom-setup", "1");
          setUsername(username.trim());
          sessionStorage.removeItem(SESSION_KEY);

          window.setTimeout(() => {
            setSetupDone(true);
            setAuthenticated(false);
          }, 850);
        }}
      />
    );
  }

  if (!authenticated) {
    return (
      <LoginScreen
        theme={theme}
        setTheme={setAndPersistTheme}
        onLogin={() => {
          sessionStorage.setItem(SESSION_KEY, "1");
          setAuthenticated(true);
        }}
      />
    );
  }

  const logout = () => {
    sessionStorage.removeItem(SESSION_KEY);
    setAuthenticated(false);
    setChangePasswordOpen(false);
  };

  return (
    <div className={`app-shell ${theme} ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar
        page={page}
        setPage={navigate}
        mobileOpen={mobileNavOpen}
        closeMobile={() => setMobileNavOpen(false)}
        collapsed={sidebarCollapsed}
        toggleCollapsed={() => setSidebarCollapsed((value) => !value)}
      />
      {mobileNavOpen && (
        <button
          type="button"
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <div className="main-shell">
        <Topbar
          theme={theme}
          setTheme={setAndPersistTheme}
          page={page}
          username={username}
          onOpenNavigation={() => setMobileNavOpen(true)}
          onLogout={logout}
          onChangePassword={() => setChangePasswordOpen(true)}
          navigate={navigate}
        />

        <main id="main-content" className="page-wrap" tabIndex={-1}>
          <WorkspacePage
            page={page}
            username={username}
            theme={theme}
            setTheme={setAndPersistTheme}
            setPage={navigate}
            onNotify={notify}
            onChangePassword={() => setChangePasswordOpen(true)}
          />
        </main>
      </div>

      {changePasswordOpen && (
        <ChangePasswordDialog
          onClose={() => setChangePasswordOpen(false)}
          onSuccess={() => {
            sessionStorage.removeItem(SESSION_KEY);
            setChangePasswordOpen(false);
            setAuthenticated(false);
            setNotice({ message: "Password changed. Sign in again to continue.", tone: "success" });
          }}
        />
      )}

      {notice && <NoticeToast notice={notice} onDismiss={() => setNotice(null)} />}
    </div>
  );
}

function AxiomMark({ small = false }: { small?: boolean }) {
  return <span className={`axiom-mark ${small ? "small" : ""}`}>A</span>;
}

function ThemeToggle({ theme, setTheme }: { theme: Theme; setTheme: (theme: Theme) => void }) {
  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      className="icon-button"
      aria-label={`Switch to ${nextTheme} theme`}
      title={`Switch to ${nextTheme} theme`}
      onClick={() => setTheme(nextTheme)}
    >
      {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  );
}

function Welcome({
  theme,
  setTheme,
  onStart,
}: {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  onStart: () => void;
}) {
  return (
    <div className={`auth-layout ${theme}`}>
      <div className="auth-topline">
        <BrandLockup />
        <ThemeToggle theme={theme} setTheme={setTheme} />
      </div>

      <div className="welcome-grid">
        <section className="welcome-copy" aria-labelledby="welcome-title">
          <StepRail current={1} />
          <p className="eyebrow">FIRST BOOT / AXIOM CONTROL CENTER</p>
          <h1 id="welcome-title">
            Build AI.
            <br />
            <span>Own AI.</span>
          </h1>
          <p className="lede">
            A local-first workspace for models, datasets, training plans, evaluation,
            and runtime decisions, kept close to the engineers making them.
          </p>
          <div className="welcome-actions">
            <button type="button" className="button primary-button" onClick={onStart}>
              Begin setup <ArrowRight size={17} />
            </button>
            <span className="quiet-note">
              <ShieldCheck size={15} /> Stored locally on this installation
            </span>
          </div>
        </section>

        <section className="preview-frame" aria-label="AXIOM workspace preview">
          <div className="preview-header">
            <div className="window-controls" aria-hidden="true"><i /><i /><i /></div>
            <span>AXIOM / CONTROL CENTER</span>
            <StatusPill tone="success">LOCAL</StatusPill>
          </div>
          <div className="preview-body">
            <div className="preview-sidebar">
              <AxiomMark small />
              <span className="preview-line active" />
              <span className="preview-line" />
              <span className="preview-line" />
              <span className="preview-line short" />
            </div>
            <div className="preview-content">
              <div className="preview-kicker">CONTROL CENTER / LOCAL WORKSPACE</div>
              <div className="preview-title">Everything important, in view.</div>
              <div className="preview-status-row">
                <div><span>Workspace</span><b>Ready for setup</b></div>
                <div><span>Runtime</span><b>Not connected</b></div>
              </div>
              <div className="preview-bars" aria-hidden="true">
                {activityBars.slice(0, 10).map((height, index) => (
                  <i key={index} style={{ height: `${height}%` }} />
                ))}
              </div>
              <div className="preview-footer"><span className="status-dot" /> Local, private, inspectable</div>
            </div>
          </div>
        </section>
      </div>

      <div className="auth-footer">
        <span>AXIOM / 0.2.0-beta.5</span>
        <span>LOCAL · PRIVATE · ENGINEERED FOR AI</span>
      </div>
    </div>
  );
}

function BrandLockup() {
  return (
    <div className="brand-lockup">
      <AxiomMark />
      <div>
        <b>AXIOM</b>
        <span>AI ENGINEERING PLATFORM</span>
      </div>
    </div>
  );
}

function StepRail({ current }: { current: 1 | 2 | 3 }) {
  return (
    <div className="step-rail" aria-label={`Setup step ${current} of 3`}>
      {[1, 2, 3].map((step) => (
        <span key={step} className={step <= current ? "active" : ""}>
          0{step}
        </span>
      ))}
    </div>
  );
}

function Setup({
  theme,
  setTheme,
  onComplete,
}: {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  onComplete: (username: string, password: string) => Promise<void>;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [reveal, setReveal] = useState(false);
  const [created, setCreated] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const passwordChecks = getPasswordChecks(password);
  const usernameValid = username.trim().length >= 3;
  const passwordsMatch = password.length > 0 && password === confirm;
  const passwordValid = Object.values(passwordChecks).every(Boolean);
  const canContinue = usernameValid && passwordValid && passwordsMatch && !saving;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canContinue) {
      return;
    }

    setSaving(true);
    setError("");

    try {
      await onComplete(username, password);
      setCreated(true);
    } catch {
      setError("Unable to save the local administrator. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={`auth-layout centered ${theme}`}>
      <div className="auth-topline">
        <BrandLockup />
        <ThemeToggle theme={theme} setTheme={setTheme} />
      </div>

      <div className="setup-shell">
        {created ? (
          <div className="success-state">
            <div className="success-mark"><Check size={26} /></div>
            <p className="eyebrow">STEP 3 OF 3 / COMPLETE</p>
            <h1>Administrator created.</h1>
      <p className="lede">Your local workspace is ready. Opening secure sign in...</p>
          </div>
        ) : (
          <form className="auth-form panel-surface" onSubmit={submit}>
            <div className="form-topline">
              <StepRail current={2} />
              <StatusPill tone="neutral">LOCAL ONLY</StatusPill>
            </div>
            <p className="eyebrow">STEP 2 OF 3 / ADMINISTRATOR</p>
            <h1>Create your administrator.</h1>
            <p className="form-intro">This account protects access to the AXIOM Control Center on this installation.</p>

            <Field label="Username" htmlFor="setup-username" hint={usernameValid ? "Username is ready" : "Use at least 3 characters"}>
              <input
                id="setup-username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="administrator"
                autoComplete="username"
                spellCheck={false}
                autoFocus
                aria-invalid={username.length > 0 && !usernameValid}
              />
            </Field>

            <Field
              label="Password"
              htmlFor="setup-password"
              hint="Use a password you do not reuse elsewhere."
              action={
                <button
                  type="button"
                  className="field-action"
                  aria-pressed={reveal}
                  onClick={() => setReveal((value) => !value)}
                >
                  {reveal ? "Hide" : "Show"}
                </button>
              }
            >
              <input
                id="setup-password"
                type={reveal ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Create a secure password"
                autoComplete="new-password"
              />
            </Field>

            <div className="requirements" aria-label="Password requirements">
              <Requirement ok={passwordChecks.length} label="8+ characters" />
              <Requirement ok={passwordChecks.upper} label="Uppercase letter" />
              <Requirement ok={passwordChecks.lower} label="Lowercase letter" />
              <Requirement ok={passwordChecks.number} label="Contains a number" />
            </div>

            <Field
              label="Confirm password"
              htmlFor="setup-confirm"
              hint={confirm.length === 0 ? "Passwords must match" : passwordsMatch ? "Passwords match" : "Passwords do not match"}
              hintTone={passwordsMatch ? "success" : "default"}
            >
              <input
                id="setup-confirm"
                type="password"
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
                placeholder="Repeat your password"
                autoComplete="new-password"
                aria-invalid={confirm.length > 0 && !passwordsMatch}
              />
            </Field>

            {error && <InlineAlert tone="danger">{error}</InlineAlert>}

            <button type="submit" className="button primary-button full-width" disabled={!canContinue}>
              {saving ? "Creating account..." : "Create administrator"}
              <ArrowRight size={17} />
            </button>
            <p className="form-note"><LockKeyhole size={14} /> Passwords are never stored in clear text. Only an encrypted verifier is persisted.</p>
          </form>
        )}
      </div>

      <div className="auth-footer"><span>AXIOM / FIRST BOOT</span><span>YOUR WORKSPACE STAYS LOCAL</span></div>
    </div>
  );
}

function getPasswordChecks(password: string) {
  return {
    length: password.length >= 8,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
  };
}

function Field({
  label,
  htmlFor,
  hint,
  hintTone = "default",
  action,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  hintTone?: "default" | "success";
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <div className="field-label-row"><label htmlFor={htmlFor}>{label}</label>{action}</div>
      <div className="input-shell">{children}</div>
      {hint && <small className={hintTone === "success" ? "success-text" : ""}>{hint}</small>}
    </div>
  );
}

function Requirement({ ok, label }: { ok: boolean; label: string }) {
  return <span className={`requirement ${ok ? "ok" : ""}`}><i>{ok ? <Check size={11} /> : null}</i>{label}</span>;
}

function LoginScreen({
  theme,
  setTheme,
  onLogin,
}: {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  onLogin: () => void;
}) {
  const [username, setUsername] = useState(getAdministratorName() === "Administrator" ? "" : getAdministratorName());
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [reveal, setReveal] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const valid = await verifyAdministrator(username, password);

      if (!valid) {
        setError("Incorrect administrator name or password.");
        return;
      }

      onLogin();
    } catch {
      setError("Unable to authenticate with the local AXIOM account.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`auth-layout login-layout ${theme}`}>
      <div className="auth-topline"><BrandLockup /><ThemeToggle theme={theme} setTheme={setTheme} /></div>
      <div className="login-shell">
        <section className="login-context">
          <p className="eyebrow">SECURE LOCAL CONTROL</p>
          <h1>Welcome back.</h1>
          <p className="lede">Continue to the workspace that keeps your models, data, and decisions close to home.</p>
          <div className="login-facts">
            <div><ShieldCheck size={16} /><span>Local administrator session</span></div>
            <div><HardDrive size={16} /><span>No cloud account required</span></div>
            <div><Clock3 size={16} /><span>10-minute inactivity timeout</span></div>
          </div>
        </section>

        <form className="login-form panel-surface" onSubmit={submit}>
          <div className="form-icon"><KeyRound size={18} /></div>
          <p className="eyebrow">ADMINISTRATOR ACCESS</p>
          <h2>Sign in</h2>
          <p className="form-intro">Use the administrator created during first boot.</p>

          <Field label="Username" htmlFor="login-username">
            <input
              id="login-username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              spellCheck={false}
              placeholder="Administrator"
              autoFocus
            />
          </Field>

          <Field
            label="Password"
            htmlFor="login-password"
            action={
              <button type="button" className="field-action" aria-pressed={reveal} onClick={() => setReveal((value) => !value)}>
                {reveal ? "Hide" : "Show"}
              </button>
            }
          >
            <input
              id="login-password"
              type={reveal ? "text" : "password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              placeholder="Password"
            />
          </Field>

          {error && <InlineAlert tone="danger" role="alert">{error}</InlineAlert>}

          <button className="button primary-button full-width" type="submit" disabled={loading || !username.trim() || !password}>
            {loading ? "Authenticating..." : "Sign in"}
            <ArrowRight size={17} />
          </button>
          <p className="form-note"><ShieldCheck size={14} /> The active session stays in this browser; credentials are not stored in clear text.</p>
        </form>
      </div>
      <div className="auth-footer"><span>AXIOM / CONTROL CENTER</span><span>LOCAL · PRIVATE · INSPECTABLE</span></div>
    </div>
  );
}

function Sidebar({
  page,
  setPage,
  mobileOpen,
  closeMobile,
  collapsed,
  toggleCollapsed,
}: {
  page: Page;
  setPage: (page: Page) => void;
  mobileOpen: boolean;
  closeMobile: () => void;
  collapsed: boolean;
  toggleCollapsed: () => void;
}) {
  return (
    <aside className={`sidebar ${mobileOpen ? "is-open" : ""}`} aria-label="Primary navigation">
      <div className="sidebar-head">
        <button
          type="button"
          className="brand-button"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={toggleCollapsed}
        >
          <AxiomMark />
          <span className="brand-button-copy"><b>AXIOM</b><small>AI ENGINEERING PLATFORM</small></span>
        </button>
        <button type="button" className="icon-button sidebar-close" aria-label="Close navigation" onClick={closeMobile}>
          <PanelLeftClose size={17} />
        </button>
      </div>

      <div className="workspace-switcher">
        <span className="workspace-avatar">A</span>
        <span><b>Local workspace</b><small>Development</small></span>
        <ChevronDown size={15} aria-hidden="true" />
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.id}>
              {item.section && <div className="nav-section">{item.section}</div>}
              <button
                type="button"
                className={`nav-item ${page === item.id ? "active" : ""}`}
                aria-current={page === item.id ? "page" : undefined}
                onClick={() => setPage(item.id)}
              >
                <Icon size={17} strokeWidth={1.8} />
                <span>{item.label}</span>
                {item.id === "diagnostics" && <StatusPill tone="warning">2</StatusPill>}
              </button>
            </div>
          );
        })}
      </nav>

      <div className="sidebar-bottom">
        <div className="core-status"><span><i className="status-dot" /> UI shell</span><b>READY</b></div>
        <p>AXIOM / BUILD AI. OWN AI.</p>
      </div>
    </aside>
  );
}

function Topbar({
  theme,
  setTheme,
  page,
  username,
  onOpenNavigation,
  onLogout,
  onChangePassword,
  navigate,
}: {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  page: Page;
  username: string;
  onOpenNavigation: () => void;
  onLogout: () => void;
  onChangePassword: () => void;
  navigate: (page: Page) => void;
}) {
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const meta = pageMeta[page];
  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return navItems.slice(0, 5);
    return navItems.filter((item) => `${item.label} ${item.description}`.toLowerCase().includes(normalized));
  }, [query]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
        setSearchOpen(true);
      }

      if (event.key === "Escape") {
        setSearchOpen(false);
        setProfileOpen(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <header className="topbar">
      <div className="topbar-context">
        <button type="button" className="mobile-menu-button icon-button" aria-label="Open navigation" onClick={onOpenNavigation}>
          <Menu size={18} />
        </button>
        <span className="breadcrumb-root">AXIOM</span><ChevronRight size={14} /><span>{meta.label}</span>
      </div>

      <div className="topbar-actions">
        <div className="command-search">
          <Search size={16} />
          <input
            ref={searchRef}
            value={query}
            placeholder="Jump to a workspace view"
            aria-label="Search workspace views"
            aria-expanded={searchOpen}
            aria-controls="workspace-search-results"
            onFocus={() => setSearchOpen(true)}
            onChange={(event) => { setQuery(event.target.value); setSearchOpen(true); }}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                setSearchOpen(false);
                (event.target as HTMLInputElement).blur();
              }
              if (event.key === "Enter" && results[0]) {
                navigate(results[0].id);
                setSearchOpen(false);
                setQuery("");
              }
            }}
          />
          <kbd><Command size={11} /> K</kbd>
          {searchOpen && (
            <div id="workspace-search-results" className="command-menu" role="listbox" aria-label="Workspace views">
              <div className="command-menu-label">NAVIGATE</div>
              {results.length > 0 ? results.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    type="button"
                    role="option"
                    aria-selected={item.id === page}
                    key={item.id}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => { navigate(item.id); setSearchOpen(false); setQuery(""); }}
                  >
                    <Icon size={16} />
                    <span><b>{item.label}</b><small>{item.description}</small></span>
                    {item.id === page && <Check size={15} />}
                  </button>
                );
              }) : <div className="command-empty">No workspace views match "{query}".</div>}
              <div className="command-hint"><kbd>↑↓</kbd> move <kbd>↵</kbd> open <kbd>esc</kbd> close</div>
            </div>
          )}
        </div>
        <ThemeToggle theme={theme} setTheme={setTheme} />
        <div className="profile-menu">
          <button type="button" className="profile-trigger" aria-expanded={profileOpen} onClick={() => setProfileOpen((value) => !value)}>
            <span className="profile-avatar">{username.charAt(0).toUpperCase()}</span>
            <span className="profile-name">{username}</span>
            <ChevronDown size={14} />
          </button>
          {profileOpen && (
            <div className="profile-dropdown" role="menu">
              <div className="profile-dropdown-head"><small>SIGNED IN AS</small><b>{username}</b></div>
              <button type="button" role="menuitem" onClick={() => { setProfileOpen(false); onChangePassword(); }}><KeyRound size={15} /> Change password</button>
              <button type="button" role="menuitem" className="danger-action" onClick={() => { setProfileOpen(false); onLogout(); }}><ArrowUpRight size={15} /> Sign out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function WorkspacePage({
  page,
  username,
  theme,
  setTheme,
  setPage,
  onNotify,
  onChangePassword,
}: {
  page: Page;
  username: string;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  setPage: (page: Page) => void;
  onNotify: (message: string, tone?: Tone) => void;
  onChangePassword: () => void;
}) {
  switch (page) {
    case "optimizer":
      return <AxiomOptimizer />;
    case "quantizer":
      return <AxiomQuantizer />;
    case "dashboard":
      return <Dashboard username={username} setPage={setPage} onNotify={onNotify} />;
    case "models":
      return <Models onNotify={onNotify} />;
    case "datasets":
      return <Datasets onNotify={onNotify} />;
    case "training":
      return <Training onNotify={onNotify} />;
    case "evaluation":
      return <Evaluation onNotify={onNotify} />;
    case "runtime":
      return <Runtime onNotify={onNotify} />;
    case "mcp":
      return <MCP onNotify={onNotify} />;
    case "diagnostics":
      return <Diagnostics onNotify={onNotify} />;
    case "logs":
      return <LogsPage onNotify={onNotify} />;
    case "settings":
      return <SettingsPage theme={theme} setTheme={setTheme} onChangePassword={onChangePassword} onNotify={onNotify} />;
  }
}

function PageHeader({
  page,
  title,
  description,
  actions,
}: {
  page: Page;
  title: ReactNode;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <p className="eyebrow">{pageMeta[page].kicker}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

function Dashboard({
  username,
  setPage,
  onNotify,
}: {
  username: string;
  setPage: (page: Page) => void;
  onNotify: (message: string, tone?: Tone) => void;
}) {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    let active = true;
    const checkHealth = () => {
      fetch(`${API_BASE}/api/health`)
        .then((response) => {
          if (!response.ok) throw new Error("Health check failed");
          return response.json() as Promise<{ status?: string }>;
        })
        .then((data) => {
          if (active) setApiStatus(data.status === "ok" ? "online" : "offline");
        })
        .catch(() => {
          if (active) setApiStatus("offline");
        });
    };
    checkHealth();
    const timer = window.setInterval(checkHealth, 10_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const apiLabel = apiStatus === "online" ? "Backend connected" : apiStatus === "checking" ? "Checking backend..." : "Backend unavailable";
  const apiTone: Tone = apiStatus === "online" ? "success" : apiStatus === "checking" ? "neutral" : "warning";

  return (
    <>
      <PageHeader
        page="dashboard"
        title={<>{getGreeting()}, {username}.</>}
        description="The interface is ready. Connect the local engine when you want live model, dataset, and runtime state here."
        actions={<button type="button" className="button secondary-button" onClick={() => setPage("diagnostics")}><CircleGauge size={16} /> Run diagnostics</button>}
      />

      <section className="status-strip" aria-label="Workspace status">
        <div className="status-strip-item primary"><StatusPill tone="success">READY</StatusPill><div><b>Local workspace</b><span>Control Center loaded</span></div></div>
        <div className="status-strip-item"><StatusPill tone={apiTone}>{apiStatus === "online" ? "ONLINE" : apiStatus === "checking" ? "CHECKING" : "OFFLINE"}</StatusPill><div><b>AXIOM backend</b><span>{apiLabel}</span></div></div>
        <div className="status-strip-item"><StatusPill tone="neutral">LOCAL</StatusPill><div><b>Session security</b><span>Administrator session active</span></div></div>
      </section>

      <div className="summary-grid">
        <SummaryCard icon={BrainCircuit} label="Model registry" value="Not connected" detail="CLI available" tone="warning" />
        <SummaryCard icon={Database} label="Dataset state" value="No report" detail="Import through CLI" tone="neutral" />
        <SummaryCard icon={Activity} label="Active runs" value="0" detail="No jobs queued" tone="neutral" />
        <SummaryCard icon={RadioTower} label="Inference" value="Offline" detail="Runtime not attached" tone="warning" />
      </div>

      <div className="dashboard-grid">
        <Surface className="activity-surface" title="Workspace activity" eyebrow="SESSION SIGNAL" action={<StatusPill tone="neutral">NO LIVE FEED</StatusPill>}>
          <div className="activity-empty">
            <div className="activity-visual" aria-hidden="true">
              <div className="activity-grid-lines" />
              <div className="activity-bars">{activityBars.map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}</div>
            </div>
            <div className="empty-copy"><h3>Waiting for a connected runtime</h3><p>This panel will show request volume and latency after a runtime endpoint is available.</p><button type="button" className="text-button" onClick={() => setPage("runtime")}>Open runtime <ArrowRight size={15} /></button></div>
          </div>
        </Surface>

        <Surface title="Next useful step" eyebrow="ORIENTATION">
          <div className="next-step">
            <div className="next-step-number">01</div>
            <div><h3>Inspect your environment</h3><p>Run the local CLI doctor before wiring models or data into a training plan.</p><button type="button" className="button small-button primary-button" onClick={() => setPage("diagnostics")}><Wrench size={15} /> Open diagnostics</button></div>
          </div>
          <div className="surface-divider" />
          <div className="inline-meta"><span><TerminalSquare size={14} /> Suggested command</span><code>axiom doctor</code></div>
        </Surface>

        <Surface className="module-surface" title="Platform map" eyebrow="WHAT AXIOM OWNS" action={<button type="button" className="text-button" onClick={() => onNotify("Module details are available in the workspace navigation.")}>View all <ArrowRight size={15} /></button>}>
          <div className="module-list">{platformModules.map((module) => <ModuleRow key={module.page} module={module} onClick={() => setPage(module.page)} />)}</div>
        </Surface>

        <Surface title="Recent activity" eyebrow="EVENTS">
          <EmptyState icon={Clock3} title="No events in this session" description="When the runtime and CLI reports are connected, validation and inference events will appear here." action={<button type="button" className="text-button" onClick={() => setPage("logs")}>Open logs <ArrowRight size={15} /></button>} />
        </Surface>
      </div>
    </>
  );
}

function SummaryCard({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: Tone }) {
  return <div className="summary-card"><div className="summary-card-head"><span>{label}</span><Icon size={17} /></div><strong>{value}</strong><div><StatusPill tone={tone}>{detail}</StatusPill></div></div>;
}

function ModuleRow({ module, onClick }: { module: (typeof platformModules)[number]; onClick: () => void }) {
  const Icon = module.icon;
  return <button type="button" className="module-row" onClick={onClick}><span className="module-icon"><Icon size={17} /></span><span className="module-copy"><b>{module.title}</b><small>{module.description}</small></span><StatusPill tone={module.tone}>{module.state}</StatusPill><ChevronRight size={15} /></button>;
}

function FeaturePage({
  page,
  children,
  actions,
}: {
  page: Exclude<Page, "dashboard">;
  children: ReactNode;
  actions?: ReactNode;
}) {
  const meta = pageMeta[page];
  return <><PageHeader page={page} title={meta.label} description={meta.description} actions={actions} />{children}</>;
}

function Models({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  return <FeaturePage page="models" actions={<button type="button" className="button primary-button" onClick={() => onNotify("Model import needs a connected runtime or the local CLI.", "warning")}><Plus size={16} /> Add model</button>}>
    <div className="info-grid"><InfoCard icon={BrainCircuit} label="Registry" value="Waiting" detail="No endpoint connected" tone="warning" /><InfoCard icon={HardDrive} label="Storage" value="N/A" detail="Not reported" tone="neutral" /><InfoCard icon={SlidersHorizontal} label="Formats" value="Ready" detail="Metadata supported" tone="success" /></div>
    <Surface title="Model registry" eyebrow="LOCAL INVENTORY" action={<button type="button" className="icon-text-button" onClick={() => onNotify("There is no model refresh endpoint in this frontend contract.", "warning")}><RefreshCcw size={15} /> Refresh</button>}>
      <EmptyState icon={BrainCircuit} title="No model inventory connected" description="The repository currently exposes model management through the AXIOM CLI. This UI does not invent a registry endpoint, so it is waiting for a real connection." action={<CliReference command="axiom model list" />} />
    </Surface>
    <ContractNote command="axiom model list" />
  </FeaturePage>;
}

function Datasets({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  return <FeaturePage page="datasets" actions={<button type="button" className="button primary-button" onClick={() => onNotify("Dataset import needs a connected runtime or the local CLI.", "warning")}><Plus size={16} /> Import dataset</button>}>
    <div className="info-grid"><InfoCard icon={Database} label="Latest report" value="None" detail="No inspection loaded" tone="neutral" /><InfoCard icon={CircleAlert} label="Validation" value="Pending" detail="No dataset selected" tone="warning" /><InfoCard icon={BarChart3} label="Token estimate" value="N/A" detail="Waiting for data" tone="neutral" /></div>
    <Surface title="Dataset workspace" eyebrow="INSPECTION QUEUE" action={<button type="button" className="icon-text-button" onClick={() => onNotify("There is no dataset listing endpoint in this frontend contract.", "warning")}><RefreshCcw size={15} /> Refresh</button>}>
      <EmptyState icon={Database} title="No dataset report yet" description="Start with a JSONL file and run inspection or validation through the CLI. The UI will stay empty until a real report contract exists." action={<CliReference command="axiom dataset inspect ./data/train.jsonl" />} />
    </Surface>
    <ContractNote command="axiom dataset validate ./data/train.jsonl" />
  </FeaturePage>;
}

function Training({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  return <FeaturePage page="training" actions={<button type="button" className="button primary-button" onClick={() => onNotify("Training execution is not exposed by the current repository contract.", "warning")}><Play size={16} /> New plan</button>}>
    <div className="info-grid"><InfoCard icon={Zap} label="Method" value="LoRA" detail="Recommended starting point" tone="success" /><InfoCard icon={Cpu} label="Hardware" value="Unknown" detail="Run axiom system info" tone="warning" /><InfoCard icon={TimerReset} label="Execution" value="Not available" detail="Planning only today" tone="neutral" /></div>
    <div className="two-column-grid">
      <Surface title="Planning checklist" eyebrow="BEFORE YOU RUN">
        <StepList steps={[{ label: "Choose a base model", detail: "Use an inspected local or Hugging Face model.", state: "pending" }, { label: "Validate the dataset", detail: "Confirm JSONL shape and duplicate behavior.", state: "pending" }, { label: "Estimate hardware fit", detail: "Select LoRA or QLoRA around available memory.", state: "ready" }, { label: "Create a reproducible config", detail: "Keep the plan close to the project axiom.yaml.", state: "ready" }]} />
      </Surface>
      <Surface title="Plan preview" eyebrow="NO ACTIVE RUN"><EmptyState icon={Hammer} title="No training plan saved" description="AXIOM can generate hardware-aware plans today; execution and job management are not part of the current contract." action={<CliReference command="axiom train plan 7" />} /></Surface>
    </div>
  </FeaturePage>;
}

function Evaluation({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  return <FeaturePage page="evaluation" actions={<button type="button" className="button primary-button" onClick={() => onNotify("Evaluation runners are not exposed by the current repository contract.", "warning")}><Play size={16} /> Run evaluation</button>}>
    <div className="info-grid"><InfoCard icon={Gauge} label="Latest score" value="N/A" detail="No report loaded" tone="neutral" /><InfoCard icon={BarChart3} label="Regression" value="N/A" detail="Needs a baseline" tone="neutral" /><InfoCard icon={TriangleAlert} label="Failures" value="N/A" detail="No assertions run" tone="neutral" /></div>
    <Surface title="Quality history" eyebrow="REPORTS"><EmptyState icon={CircleGauge} title="No evaluation history" description="The evaluation subsystem is present as a foundation, but there is no report API for this frontend to read yet." action={<CliReference command="axiom evaluation" disabled />} /></Surface>
    <Callout tone="info" title="Keep quality repeatable">When evaluation is wired in, this surface is ready for baselines, regressions, and blocking checks without changing the surrounding navigation.</Callout>
  </FeaturePage>;
}

function Runtime({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  return <FeaturePage page="runtime" actions={<button type="button" className="button secondary-button" onClick={() => onNotify("Runtime deployment needs an exposed serving contract.", "warning")}><RadioTower size={16} /> Connect runtime</button>}>
    <div className="runtime-banner"><div className="runtime-state-icon"><RadioTower size={20} /></div><div><StatusPill tone="warning">OFFLINE</StatusPill><h2>Waiting for a local engine</h2><p>No frontend endpoint or serving process is defined in this repository. The UI is ready to show runtime state when one exists.</p></div><code>axiom mcp serve</code></div>
    <div className="info-grid"><InfoCard icon={Activity} label="Requests" value="N/A" detail="No live feed" tone="neutral" /><InfoCard icon={Cpu} label="Memory" value="N/A" detail="No telemetry" tone="neutral" /><InfoCard icon={ServerCog} label="API" value="Unbound" detail="Contract required" tone="warning" /></div>
    <Surface title="Request flow" eyebrow="LIVE TELEMETRY"><EmptyState icon={RadioTower} title="No requests to display" description="Request throughput, latency, and model selection will appear here after a real runtime connector is added." action={<button type="button" className="text-button" onClick={() => onNotify("The current UI build has no runtime connector to inspect.", "warning")}>Why is this empty? <ArrowRight size={15} /></button>} /></Surface>
  </FeaturePage>;
}

function MCP({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  const servers = ["filesystem", "local-runtime", "developer-tools"];
  return <FeaturePage page="mcp" actions={<button type="button" className="button primary-button" onClick={() => onNotify("MCP server discovery needs a connected gateway.", "warning")}><Plus size={16} /> Add server</button>}>
    <div className="mcp-layout">
      <Surface title="Servers" eyebrow="GATEWAY INVENTORY">
        <div className="server-list">{servers.map((server) => <button type="button" className="server-row" key={server} onClick={() => onNotify(`${server} is a design-time placeholder until the MCP gateway is connected.`, "warning")}><span className="server-icon"><Network size={16} /></span><span><b>{server}</b><small>Waiting for gateway</small></span><StatusPill tone="neutral">OFFLINE</StatusPill></button>)}</div>
      </Surface>
      <Surface title="Inspector" eyebrow="TOOLS / RESOURCES"><EmptyState icon={Network} title="Select a connected server" description="Tool schemas, resources, prompts, and execution traces will appear here when the MCP gateway reports them." action={<button type="button" className="text-button" onClick={() => onNotify("No MCP gateway endpoint is available in the current frontend contract.", "warning")}>Check contract <ArrowRight size={15} /></button>} /></Surface>
    </div>
  </FeaturePage>;
}

function Diagnostics({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  const [scanState, setScanState] = useState<"idle" | "scanning" | "blocked">("idle");
  const [health, setHealth] = useState<{ status: "checking" | "online" | "offline"; hardware?: { cpu_name?: string; ram_gb?: number | null; gpu_name?: string } }>({ status: "checking" });

  const runScan = async () => {
    setScanState("scanning");
    try {
      const [healthResponse, hardwareResponse] = await Promise.all([
        fetch(`${API_BASE}/api/health`),
        fetch(`${API_BASE}/api/optimization/hardware`),
      ]);
      if (!healthResponse.ok || !hardwareResponse.ok) throw new Error("Backend check failed");
      const healthData = await healthResponse.json() as { status?: string };
      const hardware = await hardwareResponse.json() as { cpu_name?: string; ram_gb?: number | null; gpu_name?: string };
      setHealth({ status: healthData.status === "ok" ? "online" : "offline", hardware });
      setScanState("idle");
    } catch {
      setHealth({ status: "offline" });
      setScanState("blocked");
      onNotify("The AXIOM backend could not be reached. Start the API server and scan again.", "warning");
    }
  };

  return <FeaturePage page="diagnostics" actions={<button type="button" className="button primary-button" onClick={runScan} disabled={scanState === "scanning"}><Wrench size={16} /> {scanState === "scanning" ? "Scanning..." : "Run full scan"}</button>}>
    <div className="diagnostic-hero"><div><p className="eyebrow">WORKSPACE READINESS</p><strong>{scanState === "blocked" ? "Backend unavailable" : scanState === "scanning" ? "Checking backend..." : health.status === "online" ? "Backend connected" : "Ready to inspect"}</strong><p>{health.hardware ? `${health.hardware.cpu_name || "CPU"} · ${health.hardware.ram_gb ?? "Unknown"} GB RAM · ${health.hardware.gpu_name || "GPU unavailable"}` : "Check the API, hardware, and local session before running model workflows."}</p></div><div className={`diagnostic-ring ${scanState}`}><span>{scanState === "scanning" ? "..." : health.status === "online" ? "OK" : "N/A"}</span></div></div>
    <div className="diag-list">
      <DiagnosticRow icon={CircleCheck} title="Local administrator" detail="Authenticated session is active in this browser." state="PASS" tone="success" />
      <DiagnosticRow icon={health.status === "online" ? CircleCheck : TriangleAlert} title="AXIOM backend" detail={health.status === "online" ? "Health and hardware endpoints responded successfully." : "Run a scan to check the FastAPI backend."} state={health.status === "online" ? "PASS" : "REVIEW"} tone={health.status === "online" ? "success" : "warning"} />
      <DiagnosticRow icon={TriangleAlert} title="Model registry" detail="Use axiom model list until a real read contract is available." state="REVIEW" tone="warning" />
      <DiagnosticRow icon={CircleCheck} title="Session timeout" detail="Automatic logout is enabled after 10 minutes of inactivity." state="PASS" tone="success" />
    </div>
    {scanState === "blocked" && <Callout tone="warning" title="Backend connection failed">Start the AXIOM API and verify <code>/api/health</code> before retrying the scan.</Callout>}
    {scanState === "idle" && <button type="button" className="text-button" onClick={() => onNotify("The scan will stay honest: without a bridge, it reports the contract boundary.")}>What does this check? <ArrowRight size={15} /></button>}
  </FeaturePage>;
}

function LogsPage({ onNotify }: { onNotify: (message: string, tone?: Tone) => void }) {
  return <FeaturePage page="logs" actions={<button type="button" className="button secondary-button" onClick={() => onNotify("There are no events to filter in this session.")}><ListFilter size={16} /> Filter</button>}>
    <Surface title="Event stream" eyebrow="LIVE / LOCAL" action={<StatusPill tone="neutral">EMPTY</StatusPill>}><EmptyState icon={TerminalSquare} title="No events recorded" description="The log view is intentionally empty until a runtime, MCP gateway, or CLI report sends events to it." action={<button type="button" className="text-button" onClick={() => onNotify("Log ingestion is not connected in this frontend-only build.", "warning")}>About the boundary <ArrowRight size={15} /></button>} /></Surface>
    <div className="log-contract"><span><FileCode2 size={15} /> Expected event sources</span><code>runtime · mcp · evaluation · axiom.core</code></div>
  </FeaturePage>;
}

function SettingsPage({
  theme,
  setTheme,
  onChangePassword,
  onNotify,
}: {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  onChangePassword: () => void;
  onNotify: (message: string, tone?: Tone) => void;
}) {
  return <FeaturePage page="settings">
    <div className="settings-grid">
      <Surface title="Appearance" eyebrow="INTERFACE">
        <div className="setting-row"><div><b>Theme</b><span>Choose how AXIOM appears on this device.</span></div><div className="segmented-control" role="group" aria-label="Theme"><button type="button" className={theme === "dark" ? "active" : ""} onClick={() => setTheme("dark")}><Moon size={15} /> Dark</button><button type="button" className={theme === "light" ? "active" : ""} onClick={() => setTheme("light")}><Sun size={15} /> Light</button></div></div>
        <div className="surface-divider" />
        <div className="setting-row"><div><b>Command search</b><span>Use the keyboard shortcut to jump between workspace views.</span></div><kbd className="shortcut-key"><Command size={12} /> K</kbd></div>
      </Surface>
      <Surface title="Security" eyebrow="LOCAL ADMINISTRATOR">
        <div className="setting-row"><div><b>Administrator password</b><span>Changing it ends the current session and returns to sign in.</span></div><button type="button" className="button secondary-button" onClick={onChangePassword}><KeyRound size={15} /> Change password</button></div>
        <div className="surface-divider" />
        <div className="setting-row"><div><b>Session timeout</b><span>Automatic sign out after inactivity.</span></div><StatusPill tone="neutral">10 MINUTES</StatusPill></div>
      </Surface>
      <Surface title="Integration boundary" eyebrow="HONEST STATE">
        <Callout tone="info" title="Backend connection is available">Health, hardware, optimization, and policy-audit requests use the AXIOM FastAPI contract. Model inventory, datasets, runtime, and logs still require their dedicated endpoints.</Callout>
        <button type="button" className="text-button" onClick={() => onNotify("The dashboard and diagnostics pages use the live backend health and hardware endpoints.")}>Review integration note <ArrowRight size={15} /></button>
      </Surface>
    </div>
  </FeaturePage>;
}

function Surface({ title, eyebrow, action, children, className = "" }: { title: string; eyebrow?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`surface ${className}`}><div className="surface-head"><div>{eyebrow && <p className="surface-eyebrow">{eyebrow}</p>}<h2>{title}</h2></div>{action && <div className="surface-action">{action}</div>}</div>{children}</section>;
}

function InfoCard({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: Tone }) {
  return <div className="info-card"><div className="info-card-head"><span>{label}</span><Icon size={17} /></div><strong>{value}</strong><StatusPill tone={tone}>{detail}</StatusPill></div>;
}

function EmptyState({ icon: Icon, title, description, action }: { icon: LucideIcon; title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={20} /></div><h3>{title}</h3><p>{description}</p>{action && <div className="empty-action">{action}</div>}</div>;
}

function StatusPill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`status-pill ${tone}`}><i />{children}</span>;
}

function InlineAlert({ tone, children, role = "status" }: { tone: Tone; children: ReactNode; role?: "status" | "alert" }) {
  return <div className={`inline-alert ${tone}`} role={role}><CircleAlert size={15} />{children}</div>;
}

function Callout({ tone, title, children }: { tone: Tone; title: string; children: ReactNode }) {
  return <div className={`callout ${tone}`}><div className="callout-icon">{tone === "warning" ? <TriangleAlert size={16} /> : <CircleAlert size={16} />}</div><div><b>{title}</b><p>{children}</p></div></div>;
}

function CliReference({ command, disabled = false }: { command: string; disabled?: boolean }) {
  return <button type="button" className="cli-reference" disabled={disabled} onClick={() => navigator.clipboard?.writeText(command)}><TerminalSquare size={15} /><code>{command}</code><span>{disabled ? "Unavailable" : "Copy"}</span></button>;
}

function ContractNote({ command }: { command: string }) {
  return <div className="contract-note"><span><FileCode2 size={15} /> Current integration path</span><code>{command}</code><small>CLI contract found in this repository; no frontend HTTP endpoint was found.</small></div>;
}

function StepList({ steps }: { steps: Array<{ label: string; detail: string; state: "ready" | "pending" }> }) {
  return <div className="step-list">{steps.map((step, index) => <div className="step-list-row" key={step.label}><span className={`step-number ${step.state}`}>{step.state === "ready" ? <Check size={13} /> : String(index + 1).padStart(2, "0")}</span><div><b>{step.label}</b><small>{step.detail}</small></div><StatusPill tone={step.state === "ready" ? "success" : "neutral"}>{step.state === "ready" ? "READY" : "PENDING"}</StatusPill></div>)}</div>;
}

function DiagnosticRow({ icon: Icon, title, detail, state, tone }: { icon: LucideIcon; title: string; detail: string; state: string; tone: Tone }) {
  return <div className="diagnostic-row"><span className={`diagnostic-icon ${tone}`}><Icon size={16} /></span><div><b>{title}</b><span>{detail}</span></div><StatusPill tone={tone}>{state}</StatusPill></div>;
}

function ChangePasswordDialog({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const checks = getPasswordChecks(next);
  const complete = Object.values(checks).every(Boolean) && next.length > 0 && next === confirm;

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, saving]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSaving(true);

    try {
      const validCurrent = await verifyAdministrator(getAdministratorName(), current);
      if (!validCurrent) {
        setError("Current password is incorrect.");
        return;
      }
      if (!complete) {
        setError("The new password does not meet all requirements.");
        return;
      }
      await saveAdministrator(getAdministratorName(), next);
      setSuccess(true);
      window.setTimeout(onSuccess, 1300);
    } catch {
      setError("Unable to change the administrator password.");
    } finally {
      setSaving(false);
    }
  }

  return <div className="dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) onClose(); }}>
    <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="password-dialog-title" aria-describedby="password-dialog-description" onMouseDown={(event) => event.stopPropagation()}>
      {success ? <div className="dialog-success"><div className="success-mark"><Check size={24} /></div><p className="eyebrow">SECURITY / UPDATED</p><h2>Password changed.</h2><p id="password-dialog-description">Returning to the AXIOM sign in screen...</p></div> : <form onSubmit={submit}>
        <div className="dialog-head"><div><p className="eyebrow">SECURITY / LOCAL ADMINISTRATOR</p><h2 id="password-dialog-title">Change password</h2></div><button ref={closeRef} type="button" className="icon-button" aria-label="Close change password dialog" onClick={onClose}><X size={17} /></button></div>
        <p id="password-dialog-description" className="form-intro">Changing the password ends the current session after the update.</p>
        <Field label="Current password" htmlFor="current-password" action={<button type="button" className="field-action" aria-pressed={showCurrent} onClick={() => setShowCurrent((value) => !value)}>{showCurrent ? "Hide" : "Show"}</button>}><input id="current-password" type={showCurrent ? "text" : "password"} value={current} onChange={(event) => setCurrent(event.target.value)} autoComplete="current-password" /></Field>
        <Field label="New password" htmlFor="new-password" action={<button type="button" className="field-action" aria-pressed={showNext} onClick={() => setShowNext((value) => !value)}>{showNext ? "Hide" : "Show"}</button>}><input id="new-password" type={showNext ? "text" : "password"} value={next} onChange={(event) => setNext(event.target.value)} autoComplete="new-password" /></Field>
        <div className="requirements"><Requirement ok={checks.length} label="8+ characters" /><Requirement ok={checks.upper} label="Uppercase letter" /><Requirement ok={checks.lower} label="Lowercase letter" /><Requirement ok={checks.number} label="Contains a number" /></div>
        <Field label="Confirm new password" htmlFor="confirm-password" hint={confirm.length > 0 ? (next === confirm ? "Passwords match" : "Passwords do not match") : undefined} hintTone={next === confirm && confirm.length > 0 ? "success" : "default"}><input id="confirm-password" type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} autoComplete="new-password" /></Field>
        {error && <InlineAlert tone="danger" role="alert">{error}</InlineAlert>}
        <button type="submit" className="button primary-button full-width" disabled={!complete || saving}>{saving ? "Changing password..." : "Change password"}<ArrowRight size={17} /></button>
      </form>}
    </section>
  </div>;
}

function NoticeToast({ notice, onDismiss }: { notice: Notice; onDismiss: () => void }) {
  return <div className={`notice-toast ${notice.tone}`} role="status"><span className="notice-icon">{notice.tone === "success" ? <CircleCheck size={16} /> : notice.tone === "warning" ? <TriangleAlert size={16} /> : <CircleAlert size={16} />}</span><span>{notice.message}</span><button type="button" className="toast-close" aria-label="Dismiss notification" onClick={onDismiss}><X size={15} /></button></div>;
}

export default App;
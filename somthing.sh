#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "AXIOM release + website refresh"
echo "Repository: $ROOT"

mkdir -p .github/workflows website

# ---------------------------------------------------------------------------
# BACKUPS
# ---------------------------------------------------------------------------

if [[ -f .github/workflows/release-assets.yml ]]; then
  cp .github/workflows/release-assets.yml \
     .github/workflows/release-assets.yml.before-v020-packaging
fi

if [[ -f website/index.html ]]; then
  cp website/index.html website/index.html.before-v020-site
fi

if [[ -f website/styles.css ]]; then
  cp website/styles.css website/styles.css.before-v020-site
fi

if [[ -f website/script.js ]]; then
  cp website/script.js website/script.js.before-v020-site
fi

# ---------------------------------------------------------------------------
# WEBSITE
# ---------------------------------------------------------------------------

cat > website/index.html <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#04050a">
  <meta
    name="description"
    content="AXIOM — Build AI. Own AI. An open-source AI engineering platform from NetCore Technologies."
  >
  <title>AXIOM — Build AI. Own AI.</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap"
    rel="stylesheet"
  >
</head>

<body>
  <div class="noise"></div>
  <div class="aurora aurora-red"></div>
  <div class="aurora aurora-blue"></div>
  <div class="aurora aurora-purple"></div>

  <header class="site-header">
    <a class="brand" href="#">
      <span class="brand-mark">A</span>
      <span class="brand-copy">
        <strong>AXIOM</strong>
        <small>AI ENGINEERING PLATFORM</small>
      </span>
    </a>

    <nav class="nav">
      <a href="#platform">Platform</a>
      <a href="#workflow">Workflow</a>
      <a href="#download">Download</a>
      <a href="https://github.com/NetCore-Technologies/AXIOM-AI" target="_blank" rel="noopener">GitHub ↗</a>
    </nav>

    <a class="header-cta" href="#download">Get AXIOM</a>
  </header>

  <main>
    <section class="hero" id="platform">
      <div class="hero-copy reveal">
        <div class="eyebrow"><span class="pulse-dot"></span> OPEN SOURCE • LOCAL-FIRST • ENGINEERED FOR AI</div>

        <h1>
          Build AI.
          <span>Own AI.</span>
        </h1>

        <p class="hero-lead">
          AXIOM brings models, datasets, training, evaluation, runtime,
          diagnostics and deployment into one focused engineering workspace.
        </p>

        <div class="hero-actions">
          <a class="btn btn-primary" href="#download">Download AXIOM <span>→</span></a>
          <a class="btn btn-secondary" href="https://github.com/NetCore-Technologies/AXIOM-AI" target="_blank" rel="noopener">View on GitHub <span>↗</span></a>
        </div>

        <div class="hero-meta">
          <span>NetCore Technologies</span>
          <span>•</span>
          <span>AXIOM CONTROL CENTER</span>
        </div>
      </div>

      <div class="hero-console reveal reveal-delay-2">
        <div class="console-top">
          <div class="window-dots"><i></i><i></i><i></i></div>
          <span>AXIOM CONTROL CENTER</span>
          <span class="console-status"><i></i> READY</span>
        </div>

        <div class="console-body">
          <div class="console-grid">
            <article class="metric-card metric-wide">
              <small>SYSTEM HEALTH</small>
              <strong><span data-count="98.7">0</span>%</strong>
              <em>+1.8% from previous check</em>
              <div class="mini-chart">
                <span style="height:32%"></span>
                <span style="height:45%"></span>
                <span style="height:39%"></span>
                <span style="height:58%"></span>
                <span style="height:52%"></span>
                <span style="height:72%"></span>
                <span style="height:65%"></span>
                <span style="height:86%"></span>
                <span style="height:80%"></span>
                <span style="height:94%"></span>
              </div>
            </article>

            <article class="metric-card">
              <small>AI RUNTIME</small>
              <strong>READY</strong>
              <em>Local engine</em>
            </article>

            <article class="metric-card">
              <small>MODEL REGISTRY</small>
              <strong>SYNCED</strong>
              <em>Local models</em>
            </article>

            <article class="metric-card metric-wide">
              <div class="activity-head">
                <small>INFERENCE ACTIVITY</small>
                <span>LIVE</span>
              </div>
              <div class="activity-line" aria-hidden="true"></div>
            </article>
          </div>
        </div>

        <div class="console-footer">
          <span class="green-check">✓</span>
          Local workspace. Your models. Your engineering environment.
        </div>
      </div>
    </section>

    <section class="section" id="workflow">
      <div class="section-heading reveal">
        <div>
          <div class="eyebrow">ONE WORKSPACE</div>
          <h2>Everything between idea and deployment.</h2>
        </div>
        <p>
          A consistent control surface for the parts of AI development
          that normally live in different tools.
        </p>
      </div>

      <div class="feature-grid">
        <article class="feature-card reveal">
          <span class="feature-number">01</span>
          <div class="feature-icon gradient-icon">◎</div>
          <h3>Models</h3>
          <p>Inspect model metadata, prepare local runtimes and keep your model workflow organized.</p>
        </article>

        <article class="feature-card reveal reveal-delay-1">
          <span class="feature-number">02</span>
          <div class="feature-icon gradient-icon">◇</div>
          <h3>Datasets</h3>
          <p>Validate, clean and reason about training data before it reaches your training pipeline.</p>
        </article>

        <article class="feature-card reveal reveal-delay-2">
          <span class="feature-number">03</span>
          <div class="feature-icon gradient-icon">⌁</div>
          <h3>Training</h3>
          <p>Turn configurations into repeatable training plans with a focused engineering interface.</p>
        </article>

        <article class="feature-card reveal">
          <span class="feature-number">04</span>
          <div class="feature-icon gradient-icon">◌</div>
          <h3>Evaluation</h3>
          <p>Keep checks, results and model quality visible instead of buried in disconnected logs.</p>
        </article>

        <article class="feature-card reveal reveal-delay-1">
          <span class="feature-number">05</span>
          <div class="feature-icon gradient-icon">▣</div>
          <h3>Runtime</h3>
          <p>Monitor execution, health and resource state from the same Control Center.</p>
        </article>

        <article class="feature-card reveal reveal-delay-2">
          <span class="feature-number">06</span>
          <div class="feature-icon gradient-icon">⌬</div>
          <h3>MCP + Diagnostics</h3>
          <p>Inspect tools, requests and system health with an engineering-first diagnostic surface.</p>
        </article>
      </div>
    </section>

    <section class="section split-section">
      <div class="split-panel reveal">
        <div class="eyebrow">DESIGNED FOR ENGINEERS</div>
        <h2>Local-first without feeling local.</h2>
        <p>
          AXIOM is built around a polished desktop-grade Control Center:
          dark glass surfaces, strong information hierarchy, subtle motion
          and a visual system that stays out of your way.
        </p>

        <div class="bullet-stack">
          <div><span>✓</span><p>Dark / light workspace modes</p></div>
          <div><span>✓</span><p>Responsive Control Center UI</p></div>
          <div><span>✓</span><p>First-boot administrator experience</p></div>
          <div><span>✓</span><p>Live telemetry and diagnostics surfaces</p></div>
        </div>
      </div>

      <div class="architecture reveal reveal-delay-1">
        <div class="arch-title">
          <span>AXIOM WORKFLOW</span>
          <span class="arch-live">LOCAL</span>
        </div>

        <div class="arch-node">
          <span class="node-dot"></span>
          <div>
            <strong>Models</strong>
            <small>local model registry</small>
          </div>
        </div>

        <div class="arch-connector"></div>

        <div class="arch-node">
          <span class="node-dot"></span>
          <div>
            <strong>Data + Training</strong>
            <small>repeatable engineering flow</small>
          </div>
        </div>

        <div class="arch-connector"></div>

        <div class="arch-node">
          <span class="node-dot"></span>
          <div>
            <strong>Evaluation</strong>
            <small>checks + quality visibility</small>
          </div>
        </div>

        <div class="arch-connector"></div>

        <div class="arch-node arch-final">
          <span class="node-dot"></span>
          <div>
            <strong>Runtime</strong>
            <small>deployment + diagnostics</small>
          </div>
        </div>
      </div>
    </section>

    <section class="download-section" id="download">
      <div class="download-panel reveal">
        <div class="eyebrow">AXIOM RELEASE</div>
        <h2>Get the latest build.</h2>
        <p>
          Download the current AXIOM release for your platform.
          All release binaries and installers are published through GitHub.
        </p>

        <div class="release-badge">
          <span>v0.2.0-beta.2</span>
          <small>Latest beta</small>
        </div>

        <div class="download-grid">
          <a
            class="download-card"
            href="https://github.com/NetCore-Technologies/AXIOM-AI/releases/latest/download/AXIOM-v0.2.0-beta.2-windows-x64.exe"
          >
            <span class="download-os">WINDOWS</span>
            <strong>.EXE</strong>
            <small>Portable executable</small>
            <span class="download-arrow">↓</span>
          </a>

          <a
            class="download-card"
            href="https://github.com/NetCore-Technologies/AXIOM-AI/releases/latest/download/AXIOM-v0.2.0-beta.2-windows-x64.msi"
          >
            <span class="download-os">WINDOWS</span>
            <strong>.MSI</strong>
            <small>Installer package</small>
            <span class="download-arrow">↓</span>
          </a>

          <a
            class="download-card"
            href="https://github.com/NetCore-Technologies/AXIOM-AI/releases/latest/download/AXIOM-v0.2.0-beta.2-linux-x64.AppImage"
          >
            <span class="download-os">LINUX</span>
            <strong>.APPIMAGE</strong>
            <small>Portable desktop build</small>
            <span class="download-arrow">↓</span>
          </a>

          <a
            class="download-card"
            href="https://github.com/NetCore-Technologies/AXIOM-AI/releases/latest/download/AXIOM-v0.2.0-beta.2-linux-x64.deb"
          >
            <span class="download-os">LINUX</span>
            <strong>.DEB</strong>
            <small>Debian package</small>
            <span class="download-arrow">↓</span>
          </a>
        </div>

        <div class="download-secondary">
          <a href="https://github.com/NetCore-Technologies/AXIOM-AI/releases/latest" target="_blank" rel="noopener">
            View all release assets ↗
          </a>
          <span>Windows: .exe .msi .ps1 .bat</span>
          <span>Linux: .deb .AppImage .sh .elf</span>
        </div>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div>
      <div class="footer-brand">AXIOM</div>
      <p>Build AI. Own AI.</p>
    </div>

    <div class="footer-links">
      <a href="https://github.com/NetCore-Technologies/AXIOM-AI" target="_blank" rel="noopener">GitHub</a>
      <a href="https://github.com/NetCore-Technologies/AXIOM-AI/releases" target="_blank" rel="noopener">Releases</a>
      <a href="https://github.com/NetCore-Technologies/AXIOM-AI/tree/main/docs" target="_blank" rel="noopener">Docs</a>
      <a href="https://github.com/NetCore-Technologies/AXIOM-AI/blob/main/LICENSE" target="_blank" rel="noopener">License</a>
    </div>

    <small>© 2026 NetCore Technologies</small>
  </footer>

  <script src="./script.js"></script>
</body>
</html>
HTML

cat > website/styles.css <<'CSS'
:root {
  --bg: #04050a;
  --panel: rgba(13, 14, 21, .78);
  --panel-strong: rgba(17, 18, 27, .94);
  --line: rgba(255, 255, 255, .075);
  --line-soft: rgba(255, 255, 255, .045);

  --text: #f7f8fb;
  --muted: rgba(255, 255, 255, .58);
  --muted-2: rgba(255, 255, 255, .34);

  --red: #db285f;
  --purple: #9560e7;
  --blue: #4779ff;
  --green: #42df9d;

  --gradient:
    linear-gradient(
      100deg,
      var(--red),
      var(--purple) 48%,
      var(--blue)
    );
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  min-width: 320px;

  background:
    radial-gradient(circle at 78% 0%, rgba(71,121,255,.16), transparent 30%),
    radial-gradient(circle at 3% 89%, rgba(219,40,95,.13), transparent 31%),
    radial-gradient(circle at 52% 47%, rgba(149,96,231,.045), transparent 42%),
    var(--bg);

  color: var(--text);

  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;

  overflow-x: hidden;
}

body::before {
  content: "";

  position: fixed;
  inset: 0;
  z-index: -1;

  pointer-events: none;

  background-image:
    linear-gradient(rgba(255,255,255,.012) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.012) 1px, transparent 1px);

  background-size: 52px 52px;

  mask-image:
    radial-gradient(
      ellipse at center,
      black,
      transparent 86%
    );
}

.noise {
  position: fixed;
  inset: 0;

  z-index: 20;

  pointer-events: none;

  opacity: .025;

  background-image:
    url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.35'/%3E%3C/svg%3E");

  mix-blend-mode: screen;
}

.aurora {
  position: fixed;

  width: 500px;
  height: 500px;

  border-radius: 50%;

  filter: blur(140px);

  pointer-events: none;

  opacity: .10;

  z-index: -2;

  animation:
    drift 18s ease-in-out infinite alternate;
}

.aurora-red {
  left: -260px;
  bottom: -280px;
  background: var(--red);
}

.aurora-blue {
  right: -280px;
  top: -260px;
  background: var(--blue);

  animation-delay: -6s;
}

.aurora-purple {
  left: 42%;
  top: 36%;

  width: 330px;
  height: 330px;

  opacity: .035;

  background: var(--purple);

  animation-delay: -11s;
}

@keyframes drift {
  from {
    transform: translate3d(-10px, 10px, 0) scale(1);
  }

  to {
    transform: translate3d(24px, -18px, 0) scale(1.08);
  }
}

.site-header {
  position: sticky;

  top: 0;

  z-index: 50;

  width: min(1260px, calc(100% - 42px));

  margin: 16px auto 0;

  min-height: 66px;

  display: flex;

  align-items: center;

  gap: 26px;

  padding: 9px 10px 9px 11px;

  border:
    1px solid rgba(255,255,255,.075);

  border-radius: 17px;

  background:
    rgba(7,8,13,.72);

  box-shadow:
    0 20px 70px rgba(0,0,0,.24);

  backdrop-filter: blur(20px);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 11px;

  color: #fff;
  text-decoration: none;

  flex: 0 0 auto;
}

.brand-mark {
  width: 39px;
  height: 39px;

  display: grid;
  place-items: center;

  border-radius: 11px;

  background: var(--gradient);

  color: #fff;

  font:
    900 17px
    "Space Grotesk",
    sans-serif;

  box-shadow:
    0 0 30px rgba(219,40,95,.15),
    0 0 30px rgba(71,121,255,.10);
}

.brand-copy strong,
.brand-copy small {
  display: block;
}

.brand-copy strong {
  font:
    800 15px
    "Space Grotesk",
    sans-serif;

  letter-spacing: .12em;
}

.brand-copy small {
  margin-top: 2px;

  color: rgba(255,255,255,.37);

  font-size: 7px;

  letter-spacing: .16em;
}

.nav {
  display: flex;
  align-items: center;
  gap: 22px;

  margin-left: auto;
}

.nav a,
.header-cta {
  color: rgba(255,255,255,.56);
  text-decoration: none;

  font-size: 9px;
  font-weight: 700;

  transition:
    color .18s ease,
    transform .18s ease;
}

.nav a:hover {
  color: #fff;
  transform: translateY(-1px);
}

.header-cta {
  min-height: 37px;

  display: inline-flex;
  align-items: center;
  justify-content: center;

  padding: 0 14px;

  border-radius: 10px;

  color: #fff;

  background: var(--gradient);

  box-shadow:
    0 12px 28px rgba(219,40,95,.11);

  font-size: 8px;
}

.header-cta:hover {
  transform: translateY(-1px);
}

main {
  width: min(1260px, calc(100% - 42px));
  margin: 0 auto;
}

.hero {
  min-height: 760px;

  display: grid;

  grid-template-columns:
    minmax(0, 1fr)
    minmax(480px, .95fr);

  align-items: center;

  gap: 80px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  color: var(--blue);

  font-size: 8px;
  font-weight: 900;

  letter-spacing: .16em;
}

.pulse-dot {
  width: 7px;
  height: 7px;

  border-radius: 50%;

  background: var(--green);

  box-shadow:
    0 0 12px rgba(66,223,157,.62);

  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  50% {
    transform: scale(.78);
    box-shadow: 0 0 20px rgba(66,223,157,.35);
  }
}

.hero h1 {
  max-width: 700px;

  margin: 18px 0 22px;

  font:
    700 clamp(68px, 8vw, 108px)/.87
    "Space Grotesk",
    sans-serif;

  letter-spacing: -.075em;
}

.hero h1 span,
.section-heading h2,
.download-panel h2 {
  background:
    linear-gradient(
      92deg,
      #ff4c7c,
      #a563ff 46%,
      #4d85ff
    );

  -webkit-background-clip: text;
  background-clip: text;

  color: transparent;
}

.hero-lead {
  max-width: 610px;

  margin: 0;

  color: var(--muted);

  font-size: 15px;
  line-height: 1.85;
}

.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;

  margin-top: 30px;
}

.btn {
  min-height: 47px;

  display: inline-flex;
  align-items: center;
  justify-content: center;

  gap: 10px;

  padding: 0 17px;

  border-radius: 11px;

  text-decoration: none;

  font-size: 9px;
  font-weight: 800;

  transition:
    transform .2s ease,
    box-shadow .2s ease,
    border-color .2s ease,
    background .2s ease;
}

.btn span {
  font-size: 13px;
}

.btn-primary {
  color: #fff;

  background: var(--gradient);

  box-shadow:
    0 18px 42px rgba(219,40,95,.14),
    0 18px 42px rgba(71,121,255,.10);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow:
    0 22px 52px rgba(219,40,95,.20),
    0 22px 52px rgba(71,121,255,.15);
}

.btn-secondary {
  color: rgba(255,255,255,.72);

  border:
    1px solid rgba(255,255,255,.09);

  background:
    rgba(255,255,255,.025);
}

.btn-secondary:hover {
  color: #fff;

  transform: translateY(-2px);

  border-color:
    rgba(255,255,255,.15);
}

.hero-meta {
  display: flex;
  gap: 9px;

  margin-top: 19px;

  color: rgba(255,255,255,.24);

  font-size: 7px;

  letter-spacing: .10em;
}

.hero-console {
  padding: 11px;

  border:
    1px solid rgba(255,255,255,.09);

  border-radius: 22px;

  background:
    linear-gradient(
      145deg,
      rgba(255,255,255,.045),
      rgba(255,255,255,.011)
    );

  box-shadow:
    0 38px 100px rgba(0,0,0,.32),
    0 0 65px rgba(71,121,255,.05);

  backdrop-filter: blur(22px);

  transform:
    perspective(1600px)
    rotateY(-4deg)
    rotateX(2deg);

  transition:
    transform .45s cubic-bezier(.2,.8,.2,1);
}

.hero-console:hover {
  transform:
    perspective(1600px)
    rotateY(-1deg)
    rotateX(1deg)
    translateY(-4px);
}

.console-top {
  min-height: 31px;

  display: grid;

  grid-template-columns: 70px 1fr 75px;

  align-items: center;

  color: rgba(255,255,255,.32);

  font-size: 7px;

  letter-spacing: .12em;
}

.window-dots {
  display: flex;
  gap: 5px;
}

.window-dots i {
  width: 7px;
  height: 7px;

  border-radius: 50%;

  background: rgba(255,255,255,.16);
}

.console-top > span:nth-child(2) {
  text-align: center;
}

.console-status {
  display: flex;
  align-items: center;
  gap: 6px;

  justify-content: flex-end;

  color: rgba(255,255,255,.68);
}

.console-status i {
  width: 6px;
  height: 6px;

  border-radius: 50%;

  background: var(--green);

  box-shadow:
    0 0 10px rgba(66,223,157,.65);
}

.console-body {
  padding: 8px;

  border:
    1px solid rgba(255,255,255,.055);

  border-radius: 15px;

  background:
    rgba(4,5,10,.48);
}

.console-grid {
  display: grid;

  grid-template-columns: 1fr 1fr;

  gap: 9px;
}

.metric-card {
  min-height: 145px;

  padding: 16px;

  border:
    1px solid rgba(255,255,255,.065);

  border-radius: 13px;

  background:
    linear-gradient(
      145deg,
      rgba(255,255,255,.037),
      rgba(255,255,255,.010)
    );
}

.metric-wide {
  grid-column: span 2;
}

.metric-card small {
  color: rgba(255,255,255,.37);

  font-size: 8px;
  font-weight: 800;

  letter-spacing: .14em;
}

.metric-card strong {
  display: block;

  margin-top: 13px;

  color: #fff;

  font:
    800 28px
    "Space Grotesk",
    sans-serif;

  letter-spacing: -.05em;
}

.metric-card strong span {
  font-size: 28px;
}

.metric-card em {
  display: block;

  margin-top: 7px;

  color: var(--blue);

  font-size: 8px;

  font-style: normal;
}

.metric-card:not(.metric-wide) strong {
  font-size: 23px;
}

.activity-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.activity-head span {
  color: var(--green);

  font-size: 7px;
  font-weight: 900;

  letter-spacing: .12em;
}

.activity-line {
  position: relative;

  height: 73px;

  margin-top: 11px;

  overflow: hidden;
}

.activity-line::before {
  content: "";

  position: absolute;
  inset: 12px 0 7px;

  background:
    linear-gradient(
      180deg,
      rgba(71,121,255,.15),
      rgba(71,121,255,0)
    );

  clip-path:
    polygon(
      0 72%,
      8% 60%,
      16% 66%,
      23% 45%,
      31% 51%,
      40% 35%,
      49% 43%,
      59% 23%,
      67% 31%,
      76% 17%,
      85% 26%,
      93% 9%,
      100% 17%,
      100% 100%,
      0 100%
    );
}

.activity-line::after {
  content: "";

  position: absolute;
  left: 0;
  right: 0;
  top: 15px;

  height: 2px;

  background:
    linear-gradient(
      90deg,
      transparent 0%,
      #4779ff 8%,
      #9560e7 52%,
      #db285f 83%,
      #4779ff 100%
    );

  clip-path:
    polygon(
      0 90%,
      8% 49%,
      16% 69%,
      23% 26%,
      31% 48%,
      40% 15%,
      49% 29%,
      59% 0,
      67% 21%,
      76% 2%,
      85% 16%,
      93% 0,
      100% 8%
    );
}

.mini-chart {
  height: 45px;

  margin-top: 14px;

  display: flex;
  align-items: flex-end;

  gap: 5px;
}

.mini-chart span {
  flex: 1;

  min-width: 3px;

  border-radius: 4px 4px 1px 1px;

  background:
    linear-gradient(
      180deg,
      var(--blue),
      var(--purple) 52%,
      var(--red)
    );

  opacity: .84;

  transform-origin: bottom;

  animation: bars 3s ease-in-out infinite alternate;
}

.mini-chart span:nth-child(2n) { animation-delay: -.4s; }
.mini-chart span:nth-child(3n) { animation-delay: -.8s; }
.mini-chart span:nth-child(4n) { animation-delay: -1.2s; }

@keyframes bars {
  to {
    transform: scaleY(.78);
  }
}

.console-footer {
  display: flex;
  align-items: center;
  gap: 7px;

  padding: 11px 8px 5px;

  color: rgba(255,255,255,.35);

  font-size: 8px;
}

.green-check {
  color: var(--green);
}

.section {
  padding: 95px 0;
}

.section-heading {
  display: flex;

  align-items: end;

  justify-content: space-between;

  gap: 50px;

  margin-bottom: 32px;
}

.section-heading h2 {
  max-width: 760px;

  margin: 11px 0 0;

  font:
    700 clamp(40px, 4.8vw, 64px)/.98
    "Space Grotesk",
    sans-serif;

  letter-spacing: -.06em;
}

.section-heading > p {
  width: min(410px, 100%);

  margin: 0;

  color: var(--muted);

  font-size: 12px;

  line-height: 1.75;
}

.feature-grid {
  display: grid;

  grid-template-columns:
    repeat(3, 1fr);

  gap: 10px;
}

.feature-card {
  min-height: 235px;

  position: relative;

  padding: 24px;

  border:
    1px solid var(--line-soft);

  border-radius: 17px;

  background:
    linear-gradient(
      145deg,
      rgba(255,255,255,.033),
      rgba(255,255,255,.008)
    );

  overflow: hidden;

  transition:
    transform .24s ease,
    border-color .24s ease,
    box-shadow .24s ease;
}

.feature-card::after {
  content: "";

  position: absolute;

  width: 160px;
  height: 160px;

  right: -100px;
  bottom: -90px;

  border-radius: 50%;

  background:
    radial-gradient(
      circle,
      rgba(71,121,255,.16),
      transparent 68%
    );

  filter: blur(8px);

  transition:
    transform .3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);

  border-color:
    rgba(255,255,255,.12);

  box-shadow:
    0 24px 60px rgba(0,0,0,.18);
}

.feature-card:hover::after {
  transform: scale(1.25);
}

.feature-number {
  position: absolute;

  top: 19px;
  right: 20px;

  color: rgba(255,255,255,.18);

  font-size: 8px;
  font-weight: 900;

  letter-spacing: .12em;
}

.feature-icon {
  width: 42px;
  height: 42px;

  display: grid;
  place-items: center;

  margin-bottom: 22px;

  border-radius: 12px;

  color: #fff;

  font:
    700 19px
    "Space Grotesk";
}

.gradient-icon {
  background:
    linear-gradient(
      135deg,
      rgba(219,40,95,.24),
      rgba(149,96,231,.16),
      rgba(71,121,255,.19)
    );

  border:
    1px solid rgba(255,255,255,.06);
}

.feature-card h3 {
  margin: 0;

  font:
    700 22px
    "Space Grotesk";

  letter-spacing: -.04em;
}

.feature-card p {
  margin: 11px 0 0;

  max-width: 320px;

  color: var(--muted-2);

  font-size: 10px;
  line-height: 1.75;
}

.split-section {
  display: grid;

  grid-template-columns:
    minmax(0, 1fr)
    minmax(390px, .88fr);

  gap: 55px;

  align-items: stretch;
}

.split-panel {
  padding: 30px;

  border:
    1px solid var(--line-soft);

  border-radius: 20px;

  background:
    linear-gradient(
      145deg,
      rgba(219,40,95,.065),
      rgba(71,121,255,.025),
      rgba(255,255,255,.008)
    );
}

.split-panel h2 {
  max-width: 630px;

  margin: 12px 0;

  color: #fff;

  font:
    700 clamp(40px, 4.5vw, 62px)
    "Space Grotesk";

  letter-spacing: -.06em;
}

.split-panel > p {
  max-width: 590px;

  color: var(--muted);

  font-size: 12px;

  line-height: 1.8;
}

.bullet-stack {
  display: grid;
  gap: 11px;

  margin-top: 27px;
}

.bullet-stack div {
  display: flex;
  gap: 9px;
  align-items: center;
}

.bullet-stack span {
  color: var(--green);
}

.bullet-stack p {
  margin: 0;

  color: rgba(255,255,255,.60);

  font-size: 9px;
}

.architecture {
  min-height: 410px;

  padding: 25px;

  border:
    1px solid rgba(255,255,255,.08);

  border-radius: 20px;

  background:
    linear-gradient(
      145deg,
      rgba(255,255,255,.04),
      rgba(255,255,255,.012)
    );

  box-shadow:
    0 25px 70px rgba(0,0,0,.19);
}

.arch-title {
  display: flex;

  justify-content: space-between;

  margin-bottom: 24px;

  color: rgba(255,255,255,.38);

  font-size: 8px;
  font-weight: 900;

  letter-spacing: .14em;
}

.arch-live {
  color: var(--green);
}

.arch-node {
  min-height: 67px;

  display: flex;

  align-items: center;

  gap: 12px;

  padding: 11px 13px;

  border:
    1px solid rgba(255,255,255,.06);

  border-radius: 12px;

  background:
    rgba(255,255,255,.02);
}

.node-dot {
  width: 8px;
  height: 8px;

  flex: 0 0 8px;

  border-radius: 50%;

  background:
    linear-gradient(
      135deg,
      var(--red),
      var(--purple),
      var(--blue)
    );

  box-shadow:
    0 0 13px rgba(149,96,231,.35);
}

.arch-node strong,
.arch-node small {
  display: block;
}

.arch-node strong {
  color: #fff;

  font-size: 10px;
}

.arch-node small {
  margin-top: 4px;

  color: rgba(255,255,255,.33);

  font-size: 7px;
}

.arch-final {
  border-color:
    rgba(66,223,157,.14);

  background:
    rgba(66,223,157,.025);
}

.arch-final .node-dot {
  background: var(--green);

  box-shadow:
    0 0 15px rgba(66,223,157,.35);
}

.arch-connector {
  width: 1px;
  height: 18px;

  margin: 0 0 0 17px;

  background:
    linear-gradient(
      var(--purple),
      rgba(255,255,255,.04)
    );
}

.download-section {
  padding: 80px 0 110px;
}

.download-panel {
  position: relative;

  padding: 42px;

  overflow: hidden;

  border:
    1px solid rgba(255,255,255,.08);

  border-radius: 24px;

  background:
    radial-gradient(
      circle at 85% 15%,
      rgba(71,121,255,.10),
      transparent 33%
    ),
    radial-gradient(
      circle at 5% 90%,
      rgba(219,40,95,.10),
      transparent 31%
    ),
    linear-gradient(
      145deg,
      rgba(255,255,255,.042),
      rgba(255,255,255,.010)
    );
}

.download-panel h2 {
  margin: 12px 0;

  font:
    700 clamp(45px, 5.5vw, 70px)
    "Space Grotesk";

  letter-spacing: -.065em;
}

.download-panel > p {
  max-width: 700px;

  margin: 0;

  color: var(--muted);

  font-size: 11px;
  line-height: 1.8;
}

.release-badge {
  width: fit-content;

  display: flex;
  align-items: center;
  gap: 9px;

  margin-top: 22px;

  padding: 7px 10px;

  border:
    1px solid rgba(149,96,231,.19);

  border-radius: 999px;

  color: #fff;

  background:
    rgba(149,96,231,.07);

  font:
    800 8px
    "Space Grotesk";
}

.release-badge small {
  color: rgba(255,255,255,.36);

  font:
    600 7px
    Inter,
    sans-serif;
}

.download-grid {
  display: grid;

  grid-template-columns:
    repeat(4, 1fr);

  gap: 9px;

  margin-top: 30px;
}

.download-card {
  min-height: 155px;

  position: relative;

  display: flex;

  flex-direction: column;

  justify-content: space-between;

  padding: 17px;

  text-decoration: none;

  border:
    1px solid rgba(255,255,255,.065);

  border-radius: 15px;

  background:
    rgba(255,255,255,.021);

  transition:
    transform .22s ease,
    border-color .22s ease,
    background .22s ease;
}

.download-card:hover {
  transform: translateY(-5px);

  border-color:
    rgba(255,255,255,.13);

  background:
    linear-gradient(
      145deg,
      rgba(219,40,95,.08),
      rgba(71,121,255,.05)
    );
}

.download-os {
  color: rgba(255,255,255,.34);

  font-size: 7px;
  font-weight: 900;

  letter-spacing: .13em;
}

.download-card strong {
  margin-top: auto;

  color: #fff;

  font:
    700 26px
    "Space Grotesk";

  letter-spacing: -.04em;
}

.download-card small {
  margin-top: 4px;

  color: rgba(255,255,255,.34);

  font-size: 8px;
}

.download-arrow {
  position: absolute;

  top: 16px;
  right: 16px;

  color: rgba(255,255,255,.50);

  font-size: 15px;
}

.download-secondary {
  display: flex;
  flex-wrap: wrap;

  gap: 15px;

  margin-top: 18px;

  color: rgba(255,255,255,.26);

  font-size: 7px;
}

.download-secondary a {
  color: #4779ff;
  text-decoration: none;
}

.download-secondary a:hover {
  color: #fff;
}

.site-footer {
  width: min(1260px, calc(100% - 42px));

  margin: 0 auto;

  padding: 28px 0 45px;

  display: grid;

  grid-template-columns:
    1fr auto auto;

  gap: 30px;

  align-items: end;

  border-top:
    1px solid rgba(255,255,255,.06);

  color: rgba(255,255,255,.3);
}

.footer-brand {
  color: #fff;

  font:
    800 15px
    "Space Grotesk";

  letter-spacing: .14em;
}

.site-footer p {
  margin: 5px 0 0;

  color: rgba(255,255,255,.24);

  font-size: 8px;
}

.footer-links {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}

.footer-links a {
  color: rgba(255,255,255,.38);

  text-decoration: none;

  font-size: 8px;
}

.footer-links a:hover {
  color: #fff;
}

.site-footer > small {
  font-size: 7px;
}

.reveal {
  opacity: 0;

  transform:
    translateY(22px);

  transition:
    opacity .75s cubic-bezier(.2,.8,.2,1),
    transform .75s cubic-bezier(.2,.8,.2,1);
}

.reveal-delay-1 {
  transition-delay: .08s;
}

.reveal-delay-2 {
  transition-delay: .16s;
}

.reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
}

@media (max-width: 1040px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 30px;
    padding-top: 70px;
  }

  .hero-console {
    max-width: 760px;
  }

  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .download-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 780px) {
  .site-header {
    width: calc(100% - 20px);
    gap: 12px;
  }

  .nav {
    display: none;
  }

  .header-cta {
    margin-left: auto;
  }

  main,
  .site-footer {
    width: calc(100% - 20px);
  }

  .hero {
    min-height: auto;
    padding: 72px 0 45px;
  }

  .hero h1 {
    font-size: clamp(54px, 17vw, 86px);
  }

  .section {
    padding: 65px 0;
  }

  .section-heading {
    display: block;
  }

  .section-heading > p {
    margin-top: 15px;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }

  .split-section {
    grid-template-columns: 1fr;
  }

  .download-grid {
    grid-template-columns: 1fr 1fr;
  }

  .download-panel {
    padding: 27px 20px;
  }

  .site-footer {
    grid-template-columns: 1fr;
    align-items: start;
  }
}

@media (max-width: 520px) {
  .brand-copy small {
    display: none;
  }

  .download-grid {
    grid-template-columns: 1fr;
  }

  .console-grid {
    grid-template-columns: 1fr;
  }

  .metric-wide {
    grid-column: span 1;
  }

  .hero-console {
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }

  *,
  *::before,
  *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }

  .reveal {
    opacity: 1;
    transform: none;
  }
}
CSS

cat > website/script.js <<'JS'
(() => {
  const revealItems = document.querySelectorAll(".reveal");

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries, obs) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("is-visible");
          obs.unobserve(entry.target);
        }
      },
      {
        threshold: 0.12,
        rootMargin: "0px 0px -45px 0px",
      },
    );

    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  document.querySelectorAll("[data-count]").forEach((node) => {
    const raw = Number(node.dataset.count);
    const decimals = raw % 1 ? 1 : 0;
    const duration = 1050;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min(
        1,
        (now - start) / duration,
      );

      const eased =
        1 - Math.pow(1 - progress, 3);

      node.textContent = (raw * eased).toFixed(decimals);

      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    }

    requestAnimationFrame(tick);
  });

  const consoleCard =
    document.querySelector(".hero-console");

  if (consoleCard && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    consoleCard.addEventListener("pointermove", (event) => {
      const rect = consoleCard.getBoundingClientRect();

      const x =
        ((event.clientX - rect.left) / rect.width) - .5;

      const y =
        ((event.clientY - rect.top) / rect.height) - .5;

      consoleCard.style.transform = `
        perspective(1600px)
        rotateY(${x * 3.5 - 2}deg)
        rotateX(${y * -2.5 + 1}deg)
        translateY(-3px)
      `;
    });

    consoleCard.addEventListener("pointerleave", () => {
      consoleCard.style.transform = `
        perspective(1600px)
        rotateY(-4deg)
        rotateX(2deg)
      `;
    });
  }
})();
JS

# ---------------------------------------------------------------------------
# RELEASE WORKFLOW
# ---------------------------------------------------------------------------

cat > .github/workflows/release-assets.yml <<'YAML'
name: AXIOM Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
    inputs:
      tag:
        description: "Existing release tag to build"
        required: true
        type: string
        default: "v0.2.0-beta.2"

permissions:
  contents: write

env:
  TAG: ${{ github.event_name == 'workflow_dispatch' && inputs.tag || github.ref_name }}

jobs:
  build-ui:
    name: Build AXIOM Control Center
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Build Control Center
        run: npm run build

      - name: Upload Control Center
        uses: actions/upload-artifact@v4
        with:
          name: axiom-ui
          path: dist/
          if-no-files-found: error

  windows:
    name: Windows build
    needs: build-ui
    runs-on: windows-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download compiled UI
        uses: actions/download-artifact@v4
        with:
          name: axiom-ui
          path: dist

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install AXIOM
        shell: pwsh
        run: |
          python -m pip install --upgrade pip
          pip install .
          pip install "pyinstaller>=6.22,<7"

      - name: Build AXIOM executable
        shell: pwsh
        run: |
          Remove-Item -Recurse -Force build, out -ErrorAction SilentlyContinue
          New-Item -ItemType Directory -Force out | Out-Null

          pyinstaller `
            --noconfirm `
            --clean `
            --onefile `
            --name AXIOM `
            --add-data "dist;dist" `
            scripts/build_entry.py

          Copy-Item dist/AXIOM.exe "out/AXIOM-$env:TAG-windows-x64.exe"

      - name: Upload Windows binary
        uses: actions/upload-artifact@v4
        with:
          name: axiom-windows
          path: out/*.exe
          if-no-files-found: error

  linux:
    name: Linux build
    needs: build-ui
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download compiled UI
        uses: actions/download-artifact@v4
        with:
          name: axiom-ui
          path: dist

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install system tools
        run: |
          sudo apt-get update
          sudo apt-get install -y dpkg-dev patchelf

      - name: Install AXIOM
        run: |
          python -m pip install --upgrade pip
          pip install .
          pip install "pyinstaller>=6.22,<7"

      - name: Build AXIOM executable
        run: |
          rm -rf build out
          mkdir -p out

          pyinstaller \
            --noconfirm \
            --clean \
            --onefile \
            --name AXIOM \
            --add-data "dist:dist" \
            scripts/build_entry.py

          cp dist/AXIOM "out/AXIOM-${TAG}-linux-x64.elf"
          chmod +x "out/AXIOM-${TAG}-linux-x64.elf"

      - name: Build Debian package
        run: |
          mkdir -p pkg/DEBIAN pkg/usr/bin
          cp "out/AXIOM-${TAG}-linux-x64.elf" pkg/usr/bin/axiom
          chmod +x pkg/usr/bin/axiom

          cat > pkg/DEBIAN/control <<EOF
          Package: axiom-ai
          Version: ${TAG#v}
          Section: devel
          Priority: optional
          Architecture: amd64
          Maintainer: NetCore Technologies
          Description: AXIOM AI Engineering Platform
           Build AI. Own AI.
          EOF

          dpkg-deb --build pkg \
            "out/AXIOM-${TAG}-linux-x64.deb"

      - name: Build AppImage
        run: |
          mkdir -p AppDir/usr/bin
          cp "out/AXIOM-${TAG}-linux-x64.elf" AppDir/usr/bin/axiom
          chmod +x AppDir/usr/bin/axiom

          cat > AppDir/AppRun <<'EOF'
          #!/usr/bin/env bash
          set -e
          exec "$(dirname "$(readlink -f "$0")")/usr/bin/axiom" "$@"
          EOF
          chmod +x AppDir/AppRun

          cat > AppDir/axiom.desktop <<'EOF'
          [Desktop Entry]
          Type=Application
          Name=AXIOM
          Comment=AI Engineering Platform
          Exec=axiom
          Terminal=true
          Categories=Development;
          EOF

          curl -fsSL \
            -o appimagetool.AppImage \
            "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"

          chmod +x appimagetool.AppImage

          ARCH=x86_64 ./appimagetool.AppImage \
            AppDir \
            "out/AXIOM-${TAG}-linux-x64.AppImage"

      - name: Make Linux shell installer
        run: |
          cat > "out/AXIOM-${TAG}-linux-x64.sh" <<EOF
          #!/usr/bin/env bash
          set -euo pipefail

          SOURCE_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
          SOURCE="\${SOURCE_DIR}/AXIOM-${TAG}-linux-x64.elf"
          TARGET_DIR="\${HOME}/.local/bin"
          TARGET="\${TARGET_DIR}/axiom"

          if [[ ! -f "\${SOURCE}" ]]; then
            echo "AXIOM ELF executable not found."
            exit 1
          fi

          mkdir -p "\${TARGET_DIR}"
          install -m 0755 "\${SOURCE}" "\${TARGET}"

          echo
          echo "AXIOM installed to:"
          echo "  \${TARGET}"
          echo
          echo "Run:"
          echo "  axiom"
          EOF
          chmod +x "out/AXIOM-${TAG}-linux-x64.sh"

      - name: Upload Linux binaries
        uses: actions/upload-artifact@v4
        with:
          name: axiom-linux
          path: out/*
          if-no-files-found: error

  windows-packaging:
    name: Windows MSI + scripts
    needs: windows
    runs-on: windows-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download Windows binary
        uses: actions/download-artifact@v4
        with:
          name: axiom-windows
          path: input

      - name: Install WiX
        shell: pwsh
        run: |
          choco install wixtoolset --version=3.14.1 -y --no-progress

      - name: Create MSI, PS1 and BAT
        shell: pwsh
        run: |
          $ErrorActionPreference = "Stop"

          $exe = Get-ChildItem input -Filter *.exe |
            Select-Object -First 1

          New-Item -ItemType Directory -Force out | Out-Null
          Copy-Item $exe.FullName "out/AXIOM-$env:TAG-windows-x64.exe" -Force

          $bat = @"
          @echo off
          setlocal
          set "AXIOM_EXE=%~dp0AXIOM-$env:TAG-windows-x64.exe"
          if not exist "%AXIOM_EXE%" (
            echo AXIOM executable not found.
            exit /b 1
          )
          start "" "%AXIOM_EXE%" %*
          endlocal
          "@
          $bat | Set-Content -Encoding ASCII "out/AXIOM-$env:TAG-windows-x64.bat"

          $ps1 = @"
          param(
            [switch]`$NoStart
          )

          `$ErrorActionPreference = "Stop"

          `$source = Join-Path `$PSScriptRoot "AXIOM-$env:TAG-windows-x64.exe"
          `$targetDir = Join-Path `$env:LOCALAPPDATA "AXIOM"
          `$target = Join-Path `$targetDir "AXIOM.exe"

          if (-not (Test-Path `$source)) {
            throw "AXIOM executable not found next to installer."
          }

          New-Item -ItemType Directory -Force -Path `$targetDir | Out-Null
          Copy-Item `$source `$target -Force

          Write-Host "AXIOM installed to `$target"

          if (-not `$NoStart) {
            Start-Process `$target
          }
          "@
          $ps1 | Set-Content -Encoding UTF8 "out/AXIOM-$env:TAG-windows-x64.ps1"

          if ($env:TAG -match '^v(\d+\.\d+\.\d+)-(?:beta|b)\.(\d+)$') {
            $version = "$($Matches[1]).$($Matches[2])"
          }
          elseif ($env:TAG -match '^v(\d+\.\d+\.\d+)$') {
            $version = "$($Matches[1]).0"
          }
          else {
            throw "Unsupported AXIOM release tag: $env:TAG"
          }

          $candle = Get-ChildItem `
            "C:\Program Files (x86)\WiX Toolset v3.*\bin\candle.exe" `
            -Recurse |
            Select-Object -First 1

          $light = Get-ChildItem `
            "C:\Program Files (x86)\WiX Toolset v3.*\bin\light.exe" `
            -Recurse |
            Select-Object -First 1

          $exePath = (Resolve-Path "out/AXIOM-$env:TAG-windows-x64.exe").Path

          @"
          <?xml version="1.0" encoding="UTF-8"?>
          <Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
            <Product
              Id="*"
              Name="AXIOM"
              Language="1033"
              Version="$version"
              Manufacturer="NetCore Technologies"
              UpgradeCode="{7D9D4EF3-53A3-4CFD-9C75-1C5E8C66A120}">

              <Package
                InstallerVersion="500"
                Compressed="yes"
                InstallScope="perUser"
                Platform="x64" />

              <MajorUpgrade
                DowngradeErrorMessage="A newer version of AXIOM is already installed." />

              <MediaTemplate />

              <Directory Id="TARGETDIR" Name="SourceDir">
                <Directory Id="LocalAppDataFolder">
                  <Directory Id="INSTALLFOLDER" Name="AXIOM">
                    <Component Id="AXIOMExecutable" Guid="*">
                      <File
                        Id="AXIOMExe"
                        Source="$exePath"
                        KeyPath="yes"
                        Checksum="yes" />
                    </Component>
                  </Directory>
                </Directory>
              </Directory>

              <Feature Id="AXIOMFeature" Title="AXIOM" Level="1">
                <ComponentRef Id="AXIOMExecutable" />
              </Feature>
            </Product>
          </Wix>
          "@ | Set-Content -Encoding UTF8 wix.wxs

          Push-Location (Get-Location)
          & $candle.FullName -arch x64 wix.wxs
          & $light.FullName AXIOM.wixobj -o "out/AXIOM-$env:TAG-windows-x64.msi"
          Pop-Location

      - name: Upload Windows packages
        uses: actions/upload-artifact@v4
        with:
          name: axiom-windows-release
          path: out/*
          if-no-files-found: error

  publish:
    name: Publish AXIOM Release
    needs: [windows-packaging, linux]
    runs-on: ubuntu-latest

    steps:
      - name: Download Windows release
        uses: actions/download-artifact@v4
        with:
          name: axiom-windows-release
          path: release

      - name: Download Linux release
        uses: actions/download-artifact@v4
        with:
          name: axiom-linux
          path: release

      - name: Validate assets
        run: |
          set -euo pipefail

          [[ -f "release/AXIOM-${TAG}-windows-x64.exe" ]]
          [[ -f "release/AXIOM-${TAG}-windows-x64.msi" ]]
          [[ -f "release/AXIOM-${TAG}-windows-x64.ps1" ]]
          [[ -f "release/AXIOM-${TAG}-windows-x64.bat" ]]

          [[ -f "release/AXIOM-${TAG}-linux-x64.deb" ]]
          [[ -f "release/AXIOM-${TAG}-linux-x64.AppImage" ]]
          [[ -f "release/AXIOM-${TAG}-linux-x64.sh" ]]
          [[ -f "release/AXIOM-${TAG}-linux-x64.elf" ]]

          echo "All required AXIOM assets exist."

      - name: Generate checksums
        run: |
          cd release

          sha256sum \
            "AXIOM-${TAG}-windows-x64.msi" \
            "AXIOM-${TAG}-windows-x64.ps1" \
            "AXIOM-${TAG}-windows-x64.bat" \
            "AXIOM-${TAG}-windows-x64.exe" \
            "AXIOM-${TAG}-linux-x64.deb" \
            "AXIOM-${TAG}-linux-x64.AppImage" \
            "AXIOM-${TAG}-linux-x64.sh" \
            "AXIOM-${TAG}-linux-x64.elf" \
            > SHA256SUMS

      - name: Publish GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ env.TAG }}
          name: AXIOM ${{ env.TAG }} — GUI, First Boot & Release Packaging
          body: |
            # AXIOM ${{ env.TAG }}

            AXIOM focuses on the Control Center, first-boot experience, local administrator setup, authentication and cross-platform distribution.

            ## Highlights

            - Refined AXIOM red / purple / blue visual system
            - Refined first-boot welcome experience
            - Administrator setup with live validation
            - Login and local session flow
            - 10-minute inactivity logout
            - User menu with password change and logout
            - Dynamic administrator greeting
            - Compiled Control Center UI
            - Cross-platform release packaging

            ## Downloads

            ### Windows
            - `.exe` — portable executable
            - `.msi` — Windows installer
            - `.ps1` — PowerShell installer
            - `.bat` — Windows launcher

            ### Linux
            - `.deb` — Debian package
            - `.AppImage` — portable desktop package
            - `.sh` — local installer
            - `.elf` — raw Linux executable

            ## Verification

            `SHA256SUMS` contains checksums for all release binaries.

            ## Beta

            AXIOM is still under active development. The Control Center UI is substantially more polished, while deeper backend/runtime integration continues in upcoming releases.

            **Build AI. Own AI.**

            © 2026 NetCore Technologies
          files: release/*
          fail_on_unmatched_files: true
          overwrite_files: true
          prerelease: ${{ contains(env.TAG, '-beta.') || contains(env.TAG, '-b.') }}
          generate_release_notes: false
YAML

# ---------------------------------------------------------------------------
# LOCAL CHECKS
# ---------------------------------------------------------------------------

echo
echo "===== WEBSITE FILES ====="
wc -c website/index.html website/styles.css website/script.js

echo
echo "===== RELEASE WORKFLOW CHECK ====="
python3 - <<'PY'
from pathlib import Path
import re

p = Path(".github/workflows/release-assets.yml")
text = p.read_text()

if "Unsupported AXIOM release tag" not in text:
    raise SystemExit("Release tag validation missing")

if "v(\\d+\\.\\d+\\.\\d+)-(?:beta|b)" not in text:
    raise SystemExit("Beta release regex missing")

required = [
    "windows-x64.msi",
    "windows-x64.ps1",
    "windows-x64.bat",
    "windows-x64.exe",
    "linux-x64.deb",
    "linux-x64.AppImage",
    "linux-x64.sh",
    "linux-x64.elf",
]

missing = [item for item in required if item not in text]

if missing:
    raise SystemExit("Missing workflow asset definitions: " + ", ".join(missing))

print("Release workflow contains all 8 requested asset types.")
PY

echo
echo "===== GIT DIFF CHECK ====="
git diff --check

echo
echo "===== DONE ====="
echo
echo "Next:"
echo "  npm run lint"
echo "  npm run build"
echo
echo "Then:"
echo "  git add website .github/workflows/release-assets.yml"
echo "  git commit -m \"feat: refresh AXIOM website and release packaging\""
echo "  git push origin main"
echo
echo "For the existing tag:"
echo "  gh workflow run \"AXIOM Release\" -f tag=v0.2.0-beta.2"

# AXIOM Control Center

Standalone React/Vite frontend for AXIOM AI Engineering Platform.

Designed from the QuantumGrid visual direction: dark glass surfaces, teal/cyan telemetry accents, dense engineering information, smooth responsive layout, onboarding flow, live charts, runtime visibility, MCP inspection, diagnostics and logs.

## Included

- Welcome screen with 01 / 02 / 03 onboarding flow
- Administrator setup with live password validation
- Password number requirement fixed with deterministic `/[0-9]/` validation
- Control Center dashboard with Recharts telemetry
- Models, Datasets, Training and Evaluation views
- Runtime and MCP Inspector views
- Diagnostics and live event stream
- Settings
- Dark/light theme toggle
- Responsive navigation

## Run

```bash
npm install
npm run dev -- --host 0.0.0.0
```

The UI is intentionally self-contained for the first pass. Backend/API integration should be wired to AXIOM's Python package next, without changing the visual shell.

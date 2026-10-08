import React, { useState } from "react";

const choices = [
  ["1", "Coding"], ["2", "Cybersecurity"], ["3", "General Assistant"],
  ["4", "Reasoning"], ["5", "Research"], ["6", "Tool / Agentic AI"],
  ["7", "Creative / Writing"], ["8", "Custom"],
];

export default function Beta5OptimizerPanel() {
  const [agent, setAgent] = useState("Coding");
  const [preference, setPreference] = useState("Balanced");
  const [target, setTarget] = useState("10");
  const [context, setContext] = useState("4096");
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("");

  function optimize() {
    setStatus("Detecting hardware → analyzing model → selecting quantization → ready for benchmark");
  }

  return <section className="beta5-optimizer">
    <h2>AXIOM Agent Optimizer</h2>
    <label>Model<input value={model} onChange={e => setModel(e.target.value)} placeholder="Qwen/Qwen3-8B or local model" /></label>
    <h3>What are you building?</h3>
    <div className="beta5-choice-grid">
      {choices.map(([n, label]) =>
        <button key={n} onClick={() => setAgent(label)} className={agent === label ? "selected" : ""}>{n}) {label}</button>
      )}
    </div>
    <label>Optimization<select value={preference} onChange={e => setPreference(e.target.value)}>
      <option>Maximum speed</option><option>Balanced</option><option>Maximum quality</option>
    </select></label>
    <label>Target tokens/sec<select value={target} onChange={e => setTarget(e.target.value)}>
      <option>5</option><option>10</option><option>20</option><option>Maximum possible</option>
    </select></label>
    <label>Context length<input type="number" min="256" value={context} onChange={e => setContext(e.target.value)} /></label>
    <button onClick={optimize}>Generate optimized profile</button>
    {status && <p role="status">{status}</p>}
  </section>;
}

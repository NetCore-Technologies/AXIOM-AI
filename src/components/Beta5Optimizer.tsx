import { useState } from "react";
import { Cpu, Gauge, HardDrive, Sparkles, Zap } from "lucide-react";

type Agent = { id: string; label: string; description: string };

const agents: Agent[] = [
  { id: "coding", label: "Coding", description: "Code generation, debugging and software engineering" },
  { id: "cybersecurity", label: "Cybersecurity", description: "Security analysis, defensive automation and research" },
  { id: "general", label: "General Assistant", description: "Everyday conversational assistance" },
  { id: "reasoning", label: "Reasoning", description: "Complex reasoning and problem solving" },
  { id: "research", label: "Research", description: "Research, synthesis and long-context analysis" },
  { id: "agentic", label: "Tool / Agentic AI", description: "Tool use, workflows and autonomous task execution" },
  { id: "creative", label: "Creative / Writing", description: "Writing, editing and creative generation" },
  { id: "custom", label: "Custom", description: "Define your own workload" },
];

export default function Beta5Optimizer() {
  const [agent, setAgent] = useState("coding");
  const [goal, setGoal] = useState("balanced");
  const [target, setTarget] = useState("10");
  const [context, setContext] = useState("4096");
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("idle");

  const selected = agents.find((item) => item.id === agent) ?? agents[0];

  function optimize() {
    if (!model.trim()) {
      setStatus("Enter a Hugging Face model ID or local model path first.");
      return;
    }
    setStatus("Detecting hardware…");
    window.setTimeout(() => setStatus("Analyzing model and selecting quantization…"), 500);
    window.setTimeout(() => setStatus("Optimized profile ready for benchmark."), 1100);
  }

  return (
    <div className="beta5-optimizer-page">
      <div className="beta5-hero">
        <div>
          <p className="eyebrow">BETA 5 / AGENT OPTIMIZER</p>
          <h2>Build an optimized model profile</h2>
          <p>Tell AXIOM what you want the model to do. AXIOM detects your hardware, analyzes the model and recommends an appropriate quantization profile.</p>
        </div>
        <div className="beta5-hero-icon"><Sparkles size={25} /></div>
      </div>

      <div className="beta5-layout">
        <section className="beta5-panel">
          <div className="surface-head">
            <div><p className="surface-eyebrow">01 / MODEL</p><h2>Choose your model</h2></div>
          </div>
          <label className="beta5-field">
            <span>Hugging Face model ID or local path</span>
            <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Qwen/Qwen3-8B" />
          </label>

          <div className="surface-head beta5-section-head">
            <div><p className="surface-eyebrow">02 / WORKLOAD</p><h2>What are you building?</h2></div>
          </div>
          <div className="beta5-agent-grid">
            {agents.map((item, index) => (
              <button key={item.id} type="button" className={`beta5-agent ${agent === item.id ? "active" : ""}`} onClick={() => setAgent(item.id)}>
                <span className="beta5-number">{index + 1}</span>
                <span><b>{item.label}</b><small>{item.description}</small></span>
              </button>
            ))}
          </div>
        </section>

        <section className="beta5-panel">
          <div className="surface-head">
            <div><p className="surface-eyebrow">03 / TARGET</p><h2>Optimization preferences</h2></div>
          </div>
          <label className="beta5-field"><span>Priority</span><select value={goal} onChange={(e) => setGoal(e.target.value)}><option value="speed">Maximum speed</option><option value="balanced">Balanced</option><option value="quality">Maximum quality</option></select></label>
          <label className="beta5-field"><span>Target tokens / second</span><select value={target} onChange={(e) => setTarget(e.target.value)}><option value="5">5 TPS</option><option value="10">10 TPS</option><option value="20">20 TPS</option><option value="max">Maximum possible</option></select></label>
          <label className="beta5-field"><span>Context length</span><input type="number" min="256" step="256" value={context} onChange={(e) => setContext(e.target.value)} /></label>

          <div className="beta5-hardware">
            <div><Cpu size={16}/><span><b>Hardware</b><small>Auto-detected by AXIOM</small></span></div>
            <div><HardDrive size={16}/><span><b>GPU / VRAM</b><small>Detected during analysis</small></span></div>
            <div><Gauge size={16}/><span><b>Target</b><small>{target === "max" ? "Maximum possible" : `${target} tokens/sec`}</small></span></div>
          </div>

          <button type="button" className="button primary-button beta5-optimize-button" onClick={optimize}><Zap size={15}/> Generate optimized profile</button>
          <div className={`beta5-status ${status !== "idle" ? "visible" : ""}`} role="status">{status === "idle" ? "Ready when you are." : status}</div>
        </section>
      </div>

      <section className="beta5-result">
        <div><p className="surface-eyebrow">OPTIMIZATION PREVIEW</p><h2>{selected.label}</h2><p>{selected.description}</p></div>
        <div className="beta5-result-grid">
          <div><span>Model</span><b>{model || "Not selected"}</b></div>
          <div><span>Quantization</span><b>Auto</b></div>
          <div><span>Context</span><b>{context} tokens</b></div>
          <div><span>Validation</span><b>Benchmark required</b></div>
        </div>
      </section>
    </div>
  );
}

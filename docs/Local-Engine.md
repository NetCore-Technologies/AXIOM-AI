# AXIOM Native Engine: independent local inference execution

AXIOM Native Engine executes Llama/Mistral-family causal language models directly inside AXIOM's Python process. PyTorch supplies tensor operations and device kernels; AXIOM implements the model's forward pass, RMSNorm, rotary position embeddings (RoPE), grouped-query attention, causal/sliding-window masks, per-layer key/value cache, SwiGLU MLP, LoRA deltas, sampling and token-by-token decoding.

**It is not an Ollama wrapper.** The inference request does not start, call, or require an Ollama service. It does not call Transformers' AutoModel loader or model.generate. Checkpoint weights are read from the safetensors format and run through AXIOM's own native execution code. Tokenization is performed by the local tokenizers package using the checkpoint's tokenizer.json; AXIOM does not download a tokenizer or model.

## Install the native runtime

```bash
python -m pip install -e '.[native-inference]'
```

This extra installs PyTorch, tokenizers, and safetensors. The separate training extra retains Transformers/PEFT tooling for the existing training workflow; the native inference loop does not delegate generation to Transformers.

## Supported checkpoint format

A supported base model directory must contain:
- config.json declaring model_type llama or mistral, with ordinary unscaled RoPE.
- tokenizer.json, used locally for encoding and decoding.
- model.safetensors, or model.safetensors.index.json plus the indexed safetensors shards.
- Standard floating-point model tensors in float16, bfloat16, or float32 with expected Llama/Mistral tensor names and shapes.

The current native engine explicitly rejects GGUF, GPTQ/AWQ and other quantized weights, pickle-based pytorch_model.bin weights, custom remote model code, unsupported architectures, and non-default RoPE scaling. It never silently falls back to another execution runtime.

## Trusted model roots

The engine resolves model and adapter paths against trusted local roots and checks the post-resolution canonical path so symlink escapes are rejected. Defaults include existing models, runs, and outputs directories below the working directory; ~/models; ~/Documents/models; ~/Documents/AXIOM-AI/models and runs; the Hugging Face cache; and AXIOM's local model/fine-tuning directories.

To add a trusted location, set AXIOM_MODEL_ROOTS before starting the API. Use the platform path separator between roots (colon on Linux/macOS, semicolon on Windows). For example:

```bash
export AXIOM_MODEL_ROOTS="$HOME/models:$HOME/Documents/AXIOM-AI/runs:/mnt/data/models"
```

Only add directories you trust. Model/config/tokenizer/index/adapter assets may be symlinks only when their resolved targets remain inside one of the configured trusted roots; external-target symlinks are rejected.

## CLI

Inventory the same trusted local model roots used by the Control Center:

```bash
axiom engine discover
axiom engine discover --json
axiom engine status --json
axiom engine run --model-path /absolute/path/to/model --prompt "Hello" --max-new-tokens 64 --temperature 0
axiom engine run --model-path /absolute/path/to/model --prompt "Hello" --max-new-tokens 64 --temperature 0 --stream
```

Discovery inspects metadata and file presence only. It does not load tensors, download weights, or run inference. A listed model is a candidate for an actual local load, not a guarantee that its checkpoint tensors are compatible. The optional `--stream` mode displays cumulative decoded output as tokens arrive; `--json` remains a single final machine-readable response and cannot be combined with `--stream`.

## Control Center

Open **Runtime → AXIOM Local Engine**. Select a discovered model/adapter from the native inventory or enter its local path, then provide a prompt, output-token limit, temperature, top-p, top-k, repetition penalty and optional sampling seed. Discovery lists metadata only; weights are validated and loaded only when generation starts. **Stop generation** aborts the client stream and signals cooperative cancellation through the API into AXIOM's native prompt-prefill/token loop; cancellation is checked between transformer layers and decoding steps. A disconnect during one individual tensor kernel is acted on when that kernel yields control. **Unload model** releases AXIOM's model/tokenizer references and asks CUDA to empty its cache when applicable. Framework and OS allocators may keep some reserved memory.

A standard bias-free CAUSAL_LM LoRA adapter may be selected. AXIOM applies its A/B projection deltas in its own linear-projection path. DoRA, QALoRA, per-module rank/alpha patterns, saved replacement modules, bias-enabled adapters, unsupported target modules, and pickle adapter weights are rejected.

Before generation, use **Check adapter compatibility** to run a metadata/tensor-shape preflight against the chosen base model. The report separates CPU, NVIDIA CUDA, AMD ROCm, and Apple Metal/MPS availability and lists structural blockers by target module, rank, or shape. It does not allocate the full base model or guarantee device memory/driver/kernel success; actual generation remains the final execution test.

## Execution path

1. Validate paths against trusted roots and read bounded JSON configuration.
2. Check architecture/dimensions, safetensors index, tensor names/shapes, and tokenizer vocabulary.
3. Load safe tensors directly into PyTorch on CUDA, Metal/MPS when available, or CPU.
4. Tokenize locally and run AXIOM's embedding, RMSNorm, RoPE, grouped-query attention, KV cache, SwiGLU MLP and output-logit operations.
5. Select tokens through greedy decoding (temperature 0) or temperature/top-p sampling, passing only each new token through the cached model until the output limit or EOS token.

A checkpoint outside this contract is rejected with a compatibility error; the engine does not pretend it ran a model successfully.

## API and CLI

- GET /api/engine/status reports native dependency readiness, supported formats, execution backend, and loaded model state.
- POST /api/engine/generate runs AXIOM-native inference with a local model path, optional LoRA adapter, prompt, output-token limit and temperature.
- POST /api/engine/unload releases the model cached by the current API process.
- axiom engine status and axiom engine run use the same local engine.

Model weights must be obtained separately and placed locally, with respect for their licenses. AXIOM does not claim supplied third-party base weights were pretrained by AXIOM. Native speed and memory depend on model size, precision and device. Quantization and further architecture families need separate implementations and acceptance tests.

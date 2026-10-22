# AXIOM Engine: direct local inference

AXIOM Engine is AXIOM's own local runtime and orchestration layer for causal language models. Unlike the Ollama connector, it loads a local Transformers checkpoint directly into the Python process. Llama-architecture checkpoints are supported through the installed Transformers architecture mapping, along with other compatible causal-LM architectures exposed by that installation.

**What is ours:** the AXIOM runtime API, request bounds, local-path validation, model/adapter loading lifecycle, generation controls, and the separate bounded PyTorch LoRA training loop.

**What is not claimed:** AXIOM does not claim that third-party Llama base weights are original AXIOM-trained weights. Bring a model you have already obtained and stored locally, and respect that model's licence and usage terms. AXIOM Engine itself does not download weights, contact a model hub, or execute remote model code.

## Dependencies

Install the local training/inference extra in the same environment that runs AXIOM:

```bash
python -m pip install -e '.[training]'
```

The engine needs PyTorch and Transformers. Loading a LoRA adapter also requires PEFT.

## Model directory

Use an existing local Transformers model directory containing `config.json`, model weights and tokenizer files. The directory must be compatible with a causal language model supported by your installed Transformers version. A GGUF file or Ollama model tag is not a Transformers model directory.

## Control Center

Open **Runtime** and use the **AXIOM Local Engine** panel. Enter the absolute path to the base model directory. To generate using a trained adapter, optionally enter the adapter output directory produced by the Training panel; it must contain `adapter_config.json` and adapter weights.

The engine caches one loaded base-model/adapter pair in the API process. Selecting a different path replaces that cached runtime on the next generation request. Large models can consume substantial RAM/VRAM and generation can take several minutes on CPU.

## API

- `GET /api/engine/status` reports dependency readiness and whether a model is loaded.
- `POST /api/engine/generate` accepts `model_path`, optional `adapter_path`, `prompt`, `max_new_tokens` and `temperature`.

Prompt length is capped at 12,000 characters; generated tokens are capped at 2,048; model input context is additionally bounded by the loaded checkpoint's configuration and an AXIOM safety limit. All model and tokenizer loads use `local_files_only=True` and `trust_remote_code=False`. The engine does not overwrite base weights or adapter files.

## Limitations

- The engine is a local runtime, not a newly pretrained foundation model. Base model weights must already exist locally.
- The installed Transformers version determines which causal-LM architectures and checkpoint formats are supported.
- Runtime readiness does not guarantee that a particular checkpoint will fit available memory.
- Model downloads, remote model-hub search, GGUF conversion, and Ollama execution are separate workflows.

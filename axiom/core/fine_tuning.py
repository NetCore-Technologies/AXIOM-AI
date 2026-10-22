"""Bounded local LoRA fine-tuning using Transformers and PEFT.

No model downloads are permitted: the base model must be a local Transformers
model directory and all from_pretrained calls set local_files_only=True.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

_MAX_DATASET_BYTES = 50 * 1024 * 1024
_MAX_ROWS = 10_000
_MAX_LINE_BYTES = 1_048_576
_MAX_TEXT_CHARS = 300_000
_MAX_STEPS = 1_000
_MAX_SEQUENCE_LENGTH = 2_048
_TEXT_FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,63}$")
_PACKAGES = {"torch": "torch", "transformers": "transformers", "peft": "peft", "accelerate": "accelerate"}
_LOCAL_LOCK = threading.RLock()


class FineTuningError(RuntimeError):
    """A local fine-tuning operation could not be completed."""


class ActiveFineTuningJobError(FineTuningError):
    """Another fine-tuning job already holds the local training lock."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def jobs_directory() -> Path:
    configured = os.environ.get("AXIOM_FINETUNE_HOME", "").strip()
    base = Path(configured).expanduser() if configured else Path.home() / ".local" / "share" / "axiom" / "fine-tuning"
    return base.resolve() / "jobs"


def _lock_path() -> Path:
    return jobs_directory().parent / ".active-fine-tuning-job.json"


def runtime_status() -> dict[str, Any]:
    packages: dict[str, bool] = {}
    for label, module in _PACKAGES.items():
        try:
            packages[label] = importlib.util.find_spec(module) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            packages[label] = False
    return {
        "backend": "transformers-peft-local-lora",
        "can_start": all(packages.values()),
        "packages": packages,
        "model_loading": "local_files_only",
        "scope_note": "Optional package presence is not a compatibility or hardware-fit guarantee. The base model must already exist locally.",
    }


def require_runtime() -> None:
    status = runtime_status()
    missing = [name for name, present in status["packages"].items() if not present]
    if missing:
        raise FineTuningError(
            "Local fine-tuning dependencies are missing: " + ", ".join(missing) + ". "
            "Install the optional extras in your active environment with: python -m pip install -e '.[training]'"
        )


def _resolve_existing(value: str, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")
    try:
        return Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError(f"{label} must point to an existing local path.") from None


def _load_texts(dataset_path: Path, text_field: str) -> list[str]:
    if dataset_path.stat().st_size > _MAX_DATASET_BYTES:
        raise ValueError(f"Dataset exceeds the {_MAX_DATASET_BYTES // (1024 * 1024)} MiB limit.")
    texts: list[str] = []
    try:
        with dataset_path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if len(line.encode("utf-8")) > _MAX_LINE_BYTES:
                    raise ValueError(f"Dataset line {line_number} exceeds the 1 MiB line limit.")
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    raise ValueError(f"Dataset line {line_number} is not valid JSON.") from None
                if not isinstance(record, dict):
                    raise ValueError(f"Dataset line {line_number} must contain a JSON object.")
                value = record.get(text_field)
                if value is None and isinstance(record.get("prompt"), str) and isinstance(record.get("completion"), str):
                    value = record["prompt"] + "\n" + record["completion"]
                if value is None and isinstance(record.get("messages"), list):
                    parts: list[str] = []
                    for message in record["messages"]:
                        if isinstance(message, dict) and isinstance(message.get("content"), str):
                            role = message.get("role")
                            parts.append((f"{role}: " if isinstance(role, str) and role else "") + message["content"])
                    value = "\n".join(parts) if parts else None
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"Dataset line {line_number} needs a non-empty string in '{text_field}', "
                        "or string prompt/completion fields, or messages with content strings."
                    )
                if len(value) > _MAX_TEXT_CHARS:
                    raise ValueError(f"Dataset line {line_number} text exceeds the {_MAX_TEXT_CHARS:,}-character limit.")
                texts.append(value.strip())
                if len(texts) > _MAX_ROWS:
                    raise ValueError(f"Dataset exceeds the {_MAX_ROWS:,}-row limit.")
    except UnicodeDecodeError:
        raise ValueError("Dataset must be UTF-8 encoded JSONL.") from None
    if not texts:
        raise ValueError("Dataset contains no non-empty training records.")
    return texts


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate user-supplied paths and conservative LoRA controls before creating a job."""
    if not isinstance(config, dict):
        raise ValueError("Fine-tuning configuration must be a mapping.")
    model_path = _resolve_existing(config.get("model_path", ""), "Base model directory")
    if not model_path.is_dir() or not (model_path / "config.json").is_file():
        raise ValueError("Base model must be an existing local Transformers model directory containing config.json.")
    dataset_path = _resolve_existing(config.get("dataset_path", ""), "Training dataset")
    if not dataset_path.is_file():
        raise ValueError("Training dataset must be a local JSONL file.")
    output_raw = config.get("output_dir", "")
    if not isinstance(output_raw, str) or not output_raw.strip():
        raise ValueError("Adapter output directory is required.")
    try:
        output_dir = Path(output_raw).expanduser().resolve(strict=False)
        parent = output_dir.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("The parent of the adapter output directory must already exist locally.") from None
    if not parent.is_dir():
        raise ValueError("The parent of the adapter output directory must be a directory.")
    if output_dir == model_path or model_path in output_dir.parents or output_dir in model_path.parents:
        raise ValueError("Adapter output and base model directories must not overlap.")
    if output_dir == dataset_path or output_dir == dataset_path.parent:
        raise ValueError("Adapter output must not overwrite the training dataset or its directory.")
    if output_dir.exists():
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise ValueError("Adapter output must be a new directory or an existing empty directory.")
    text_field = config.get("text_field", "text")
    if not isinstance(text_field, str) or not _TEXT_FIELD.fullmatch(text_field):
        raise ValueError("Text field must be a simple JSON field name (letters, digits, underscore, dot, or hyphen).")
    max_steps = config.get("max_steps", 20)
    sequence_length = config.get("sequence_length", 512)
    lora_rank = config.get("lora_rank", 8)
    learning_rate = config.get("learning_rate", 0.0001)
    if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 1 <= max_steps <= _MAX_STEPS:
        raise ValueError(f"Maximum training steps must be between 1 and {_MAX_STEPS}.")
    if isinstance(sequence_length, bool) or not isinstance(sequence_length, int) or not 32 <= sequence_length <= _MAX_SEQUENCE_LENGTH:
        raise ValueError(f"Sequence length must be between 32 and {_MAX_SEQUENCE_LENGTH} tokens.")
    if isinstance(lora_rank, bool) or not isinstance(lora_rank, int) or not 1 <= lora_rank <= 64:
        raise ValueError("LoRA rank must be an integer between 1 and 64.")
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)) or not 0.000001 <= float(learning_rate) <= 0.01:
        raise ValueError("Learning rate must be between 0.000001 and 0.01.")
    result = {
        "model_path": str(model_path),
        "dataset_path": str(dataset_path),
        "output_dir": str(output_dir),
        "text_field": text_field,
        "max_steps": max_steps,
        "sequence_length": sequence_length,
        "learning_rate": float(learning_rate),
        "lora_rank": lora_rank,
    }
    # Read and validate the dataset before any training process starts.
    _load_texts(dataset_path, text_field)
    return result


def _job_path(job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError("Invalid fine-tuning job ID.")
    return jobs_directory() / f"{job_id}.json"


def _write_job(job: dict[str, Any]) -> None:
    folder = jobs_directory()
    folder.mkdir(parents=True, exist_ok=True)
    target = _job_path(job["id"])
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, target)


def _read_job(job_id: str) -> dict[str, Any] | None:
    path = _job_path(job_id)
    if not path.is_file():
        return None
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise FineTuningError("Saved fine-tuning job state could not be read.") from None
    return job if isinstance(job, dict) else None


def _recover_if_stale(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("status") in {"queued", "running"} and not _pid_is_alive(job.get("runner_pid")):
        job = dict(job)
        reason = "The AXIOM process exited before this training job completed. Start a new job after checking resources."
        job.update(status="failed", error=reason, finished_at=_now(), updated_at=_now())
        job["logs"] = [*job.get("logs", []), f"Failed: {reason}"][-80:]
        _write_job(job)
    return job


def get_job(job_id: str) -> dict[str, Any] | None:
    job = _read_job(job_id)
    return _recover_if_stale(job) if job is not None else None


def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("Job list limit must be between 1 and 100.")
    folder = jobs_directory()
    if not folder.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in folder.glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and re.fullmatch(r"[0-9a-f]{32}", str(value.get("id", ""))):
                records.append(_recover_if_stale(value))
        except (OSError, json.JSONDecodeError):
            continue
    records.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return records[:limit]


def _pid_is_alive(pid: Any) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _acquire_lock(job_id: str) -> None:
    lock = _lock_path()
    lock.parent.mkdir(parents=True, exist_ok=True)
    with _LOCAL_LOCK:
        if lock.exists():
            try:
                current = json.loads(lock.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                current = {}
            if _pid_is_alive(current.get("pid")):
                raise ActiveFineTuningJobError("Another local fine-tuning job is active. Check `axiom train jobs` before starting another.")
            try:
                lock.unlink(missing_ok=True)
            except OSError:
                raise ActiveFineTuningJobError("The fine-tuning lock could not be recovered safely.") from None
        payload = json.dumps({"job_id": job_id, "pid": os.getpid(), "created_at": _now()})
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise ActiveFineTuningJobError("Another local fine-tuning job is starting. Try again shortly.") from None
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)


def _release_lock(job_id: str) -> None:
    lock = _lock_path()
    with _LOCAL_LOCK:
        try:
            current = json.loads(lock.read_text(encoding="utf-8"))
            if current.get("job_id") == job_id and current.get("pid") == os.getpid():
                lock.unlink(missing_ok=True)
        except (OSError, json.JSONDecodeError):
            pass


def _new_job(config: dict[str, Any]) -> dict[str, Any]:
    validated = validate_config(config)
    require_runtime()
    job_id = uuid.uuid4().hex
    _acquire_lock(job_id)
    now = _now()
    job: dict[str, Any] = {
        "schema_version": 1,
        "id": job_id,
        "runner_pid": os.getpid(),
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "config": validated,
        "completed_steps": 0,
        "loss": None,
        "error": None,
        "logs": ["Job queued. The base model and dataset are local inputs; no weights will be downloaded."],
    }
    try:
        _write_job(job)
    except Exception:
        _release_lock(job_id)
        raise
    return job


def start_finetuning_job(config: dict[str, Any]) -> dict[str, Any]:
    """Validate inputs, persist a job, and run it in a single background thread."""
    job = _new_job(config)
    worker = threading.Thread(target=execute_finetuning_job, args=(job["id"],), name=f"axiom-lora-{job['id'][:8]}", daemon=True)
    try:
        worker.start()
    except RuntimeError:
        _update_job(job["id"], status="failed", error="Could not start the local training worker.", finished_at=_now())
        _release_lock(job["id"])
        raise FineTuningError("Could not start the local training worker.") from None
    return get_job(job["id"]) or job


def run_finetuning_inline(config: dict[str, Any], on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Run a job synchronously for CLI use, retaining the same job history format."""
    job = _new_job(config)
    execute_finetuning_job(job["id"], on_progress=on_progress)
    return get_job(job["id"]) or job


def _update_job(job_id: str, **changes: Any) -> dict[str, Any]:
    with _LOCAL_LOCK:
        job = _read_job(job_id)
        if job is None:
            raise FineTuningError("Fine-tuning job was not found.")
        job.update(changes)
        job["updated_at"] = _now()
        _write_job(job)
        return job


def _load_training_texts(config: dict[str, Any]) -> list[str]:
    return _load_texts(Path(config["dataset_path"]), config["text_field"])


def _run_transformers(config: dict[str, Any], progress: Callable[[int, float | None], None]) -> dict[str, Any]:
    """Load local model weights and perform bounded causal-LM LoRA training."""
    try:
        import torch
        from peft import LoraConfig, TaskType, get_peft_model
        from torch.utils.data import Dataset
        from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling, Trainer, TrainerCallback, TrainingArguments
    except (ImportError, OSError) as exc:
        raise FineTuningError(
            "Transformers/PEFT training dependencies could not be imported. Install them with: python -m pip install -e '.[training]'"
        ) from None

    texts = _load_training_texts(config)
    model_path = config["model_path"]
    output_dir = Path(config["output_dir"])
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FineTuningError("Adapter output directory is no longer empty; refusing to overwrite existing files.")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Explicit local_files_only blocks implicit downloads from Hugging Face.
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    if tokenizer.pad_token is None:
        if tokenizer.eos_token is None:
            raise FineTuningError("Tokenizer needs an existing pad_token or eos_token to train safely.")
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    model.config.use_cache = False
    leaf_names = {
        module_name.rsplit(".", 1)[-1]
        for module_name, module in model.named_modules()
        if (isinstance(module, torch.nn.Linear) or module.__class__.__name__ == "Conv1D") and module_name
    }
    preferred = [
        "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj",
        "c_attn", "c_proj", "query_key_value", "Wqkv", "query", "value",
    ]
    targets = [name for name in preferred if name in leaf_names]
    if not targets:
        raise FineTuningError(
            "This model architecture exposes no recognised linear projection names for automatic LoRA targeting. "
            "Supported common names include q_proj/v_proj and c_attn; no model code was downloaded or executed."
        )
    lora = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config["lora_rank"],
        lora_alpha=max(8, config["lora_rank"] * 2),
        lora_dropout=0.05,
        target_modules=targets,
        bias="none",
    )
    model = get_peft_model(model, lora)

    class TextDataset(Dataset):
        def __len__(self) -> int:
            return len(texts)

        def __getitem__(self, index: int) -> dict[str, Any]:
            encoded = tokenizer(
                texts[index],
                truncation=True,
                max_length=config["sequence_length"],
                padding="max_length",
                return_tensors="pt",
            )
            return {key: value.squeeze(0) for key, value in encoded.items()}

    class ReportProgress(TrainerCallback):
        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            values = logs or {}
            try:
                loss = float(values["loss"]) if values.get("loss") is not None else None
            except (TypeError, ValueError):
                loss = None
            progress(int(getattr(state, "global_step", 0)), loss)
            return control

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        max_steps=config["max_steps"],
        per_device_train_batch_size=1,
        gradient_accumulation_steps=1,
        learning_rate=config["learning_rate"],
        logging_steps=1,
        save_strategy="no",
        report_to=[],
        fp16=bool(torch.cuda.is_available()),
        dataloader_num_workers=0,
        disable_tqdm=True,
        remove_unused_columns=False,
        optim="adamw_torch",
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=TextDataset(),
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        callbacks=[ReportProgress()],
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    adapter_files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    if not any(name in adapter_files for name in ("adapter_model.safetensors", "adapter_model.bin")):
        raise FineTuningError("Training finished but a PEFT adapter weight file was not produced.")
    return {"output_dir": str(output_dir), "adapter_files": adapter_files, "target_modules": targets, "dataset_rows": len(texts), "max_steps": config["max_steps"]}


def execute_finetuning_job(job_id: str, on_progress: Callable[[dict[str, Any]], None] | None = None) -> None:
    job = _read_job(job_id)
    if job is None:
        return
    try:
        _update_job(job_id, status="running", started_at=_now(), error=None, logs=[*job.get("logs", []), "Loading local tokenizer/model and preparing LoRA adapters."][-80:])

        def progress(step: int, loss: float | None) -> None:
            current = _read_job(job_id)
            if current is None:
                return
            message = f"Step {max(0, step)}/{current['config']['max_steps']}" + (f" · loss {loss:.5f}" if loss is not None else "")
            updated = _update_job(
                job_id,
                completed_steps=min(max(0, step), current["config"]["max_steps"]),
                loss=loss,
                logs=[*current.get("logs", []), message][-80:],
            )
            if on_progress:
                on_progress(updated)

        result = _run_transformers(job["config"], progress)
        current = _read_job(job_id) or job
        _update_job(
            job_id,
            status="completed",
            finished_at=_now(),
            completed_steps=current["config"]["max_steps"],
            result=result,
            error=None,
            logs=[*current.get("logs", []), "Training completed; PEFT adapter files were written to the selected output directory."][-80:],
        )
    except Exception as exc:
        # Failure details are clipped; avoid dumping full local environment/configs.
        reason = str(exc).replace("\r", " ").replace("\n", " ").strip()[:500] or type(exc).__name__
        try:
            current = _read_job(job_id) or job
            _update_job(
                job_id,
                status="failed",
                finished_at=_now(),
                error=reason,
                logs=[*current.get("logs", []), f"Failed: {reason}"][-80:],
            )
        except Exception:
            pass
    finally:
        _release_lock(job_id)

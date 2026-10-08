from __future__ import annotations
import os, platform, shutil, subprocess

def _cmd(*args):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

def detect_hardware():
    gpu = "CPU"
    vram_mb = None
    backend = "cpu"

    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        name = _cmd(nvidia, "--query-gpu=name", "--format=csv,noheader")
        mem = _cmd(nvidia, "--query-gpu=memory.total", "--format=csv,noheader,nounits")
        if name:
            gpu = name.splitlines()[0].strip()
            backend = "cuda"
        if mem:
            try:
                vram_mb = int(mem.splitlines()[0].strip())
            except ValueError:
                pass

    if backend == "cpu" and shutil.which("rocminfo"):
        gpu = "AMD GPU"
        backend = "rocm"

    if platform.system() == "Darwin" and platform.machine() == "arm64":
        gpu = "Apple Silicon"
        backend = "mps"

    return {
        "os": platform.system(),
        "arch": platform.machine(),
        "cpu_cores": os.cpu_count() or 1,
        "ram_gb": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3, 1)
        if hasattr(os, "sysconf") else None,
        "gpu": gpu,
        "vram_mb": vram_mb,
        "backend": backend,
    }

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SystemInfo:
    os: str
    arch: str
    cpu_count: int
    ram_gb: float
    gpu_available: bool
    gpu_name: str
    vram_gb: float
    disk_free_gb: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "os": self.os,
            "arch": self.arch,
            "cpu_count": self.cpu_count,
            "ram_gb": round(self.ram_gb, 2),
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "vram_gb": round(self.vram_gb, 2),
            "disk_free_gb": round(self.disk_free_gb, 2),
        }


def _ram_gb() -> float:
    path = Path("/proc/meminfo")
    if not path.exists():
        return 0.0

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024 / 1024
    except (OSError, ValueError):
        return 0.0

    return 0.0


def _nvidia() -> tuple[bool, str, float]:
    binary = shutil.which("nvidia-smi")
    if not binary:
        return False, "", 0.0

    try:
        import subprocess

        result = subprocess.run(
            [
                binary,
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return False, "", 0.0

        first = result.stdout.strip().splitlines()[0]
        name, memory = [x.strip() for x in first.split(",", 1)]
        return True, name, float(memory) / 1024
    except (OSError, ValueError):
        return False, "", 0.0


def inspect_system() -> SystemInfo:
    gpu, gpu_name, vram = _nvidia()

    free_gb = 0.0
    try:
        free_gb = shutil.disk_usage(Path.cwd()).free / 1024**3
    except OSError:
        import logging as _axiom_logging

        _axiom_logging.getLogger(__name__).debug(
            "intentionally ignored exception", exc_info=True
        )

    return SystemInfo(
        os=platform.system(),
        arch=platform.machine(),
        cpu_count=os.cpu_count() or 1,
        ram_gb=_ram_gb(),
        gpu_available=gpu,
        gpu_name=gpu_name,
        vram_gb=vram,
        disk_free_gb=free_gb,
    )

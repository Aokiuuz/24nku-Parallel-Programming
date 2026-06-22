#!/usr/bin/env python3
"""Build the AUP upload ZIP with POSIX member paths."""

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "PCFG_GPU_real.zip"
CHECKSUM = ROOT / "PCFG_GPU_real.zip.sha256"
FILES = {
    "Makefile": "Makefile",
    "run_real.sh": "run_real.sh",
    "src/gpu/pcfg_gpu_generate.h": "src/gpu/pcfg_gpu_generate.h",
    "src/gpu/pcfg_gpu_generate.hip": "src/gpu/pcfg_gpu_generate.hip",
    "src/gpu/pcfg_gpu_test.cpp": "src/gpu/pcfg_gpu_test.cpp",
    "src/gpu/pcfg_real_end_to_end.cpp": "src/gpu/pcfg_real_end_to_end.cpp",
    "pcfg_gpu/guess_mpi_advanced/PCFG.h": "pcfg_gpu/guess_mpi_advanced/PCFG.h",
    "pcfg_gpu/guess_mpi_advanced/train.cpp": "pcfg_gpu/guess_mpi_advanced/train.cpp",
    "pcfg_gpu/guess_mpi_advanced/guessing.cpp": "pcfg_gpu/guess_mpi_advanced/guessing.cpp",
    "scripts/run_real_pcfg.sh": "scripts/run_real_pcfg.sh",
    "scripts/analyze_real_results.py": "scripts/analyze_real_results.py",
    "scripts/plot_real_results.py": "scripts/plot_real_results.py",
    "docs/AUP真实PCFG端到端运行指南.md": "RUN_GUIDE.md",
}


def main() -> None:
    missing = [source for source in FILES if not (ROOT / source).is_file()]
    if missing:
        raise SystemExit(f"Missing package inputs: {', '.join(missing)}")
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for source, member in FILES.items():
            archive.write(ROOT / source, member)
        archive.writestr(
            "data/README.md",
            "Place the optional fallback training subset at data/Rockyou-1m.txt.\n",
        )
    with ZipFile(OUTPUT) as archive:
        bad = [name for name in archive.namelist() if "\\" in name or name.startswith("/")]
        if bad:
            raise SystemExit(f"Invalid ZIP member paths: {bad}")
        entry_count = len(archive.namelist())
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    CHECKSUM.write_text(f"{digest}  {OUTPUT.name}\n", encoding="ascii")
    print(f"Created {OUTPUT.name}: {entry_count} entries, sha256={digest}")


if __name__ == "__main__":
    main()

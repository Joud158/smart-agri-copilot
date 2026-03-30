from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/app")
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

PROFILES = [
    {
        "name": "baseline_localdet_top5_900_180",
        "env": {
            "EMBEDDING_PROVIDER": "local_deterministic",
            "TOP_K": "5",
            "RAG_CHUNK_SIZE": "900",
            "RAG_CHUNK_OVERLAP": "180",
        },
    },
    {
        "name": "baseline_localdet_top3_700_120",
        "env": {
            "EMBEDDING_PROVIDER": "local_deterministic",
            "TOP_K": "3",
            "RAG_CHUNK_SIZE": "700",
            "RAG_CHUNK_OVERLAP": "120",
        },
    },
]


def run_json(cmd: list[str], env: dict[str, str]) -> dict:
    output = subprocess.check_output(cmd, env=env, text=True)
    return json.loads(output)


def main() -> None:
    comparison: list[dict] = []
    base_env = os.environ.copy()

    for profile in PROFILES:
        env = {**base_env, **profile["env"]}
        subprocess.check_call([sys.executable, "/app/scripts/ingest_to_qdrant.py"], env=env)
        retrieval = run_json([sys.executable, "/app/scripts/evaluate_retrieval.py"], env=env)
        generation = run_json([sys.executable, "/app/scripts/evaluate_generation.py"], env=env)
        comparison.append(
            {
                "profile": profile["name"],
                "env": profile["env"],
                "retrieval_macro": retrieval["macro"],
                "generation_macro": generation["macro"],
            }
        )

    report = {"profiles": comparison}
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

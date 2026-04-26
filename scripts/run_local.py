from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arquisys_ai.graph.workflow import ArquiSysWorkflow  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ArquiSys AI local workflow")
    parser.add_argument("--request", help="User requirement text", default=None)
    args = parser.parse_args()

    user_request = args.request if args.request else input("Describe el diagrama: ").strip()
    workflow = ArquiSysWorkflow()
    result = workflow.run(user_request)

    print("\n[ANALISIS]")
    print(json.dumps(result.analysis.to_dict(), indent=2, ensure_ascii=False))

    if result.architecture is None:
        print("\n[ESTADO]")
        print("Falta contexto. Responde las preguntas del analista para continuar.")
        return

    output_kind = result.architecture.diagram_format.value.upper()
    print(f"\n[SALIDA - {output_kind}]")
    print(result.architecture.code)

    if result.architecture.warnings:
        print("\n[ADVERTENCIAS]")
        for warning in result.architecture.warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()

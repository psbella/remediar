"""
tests/conftest.py
Si algún test falla, genera tests/debug_update_failed.txt
con el detalle de todos los fallos para facilitar el diagnóstico.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

DEBUG_PATH = Path(__file__).parent / "debug_update_failed.txt"


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    failed = terminalreporter.stats.get("failed", [])

    if not failed:
        # Todo OK — borrar archivo de debug anterior si existía
        if DEBUG_PATH.exists():
            DEBUG_PATH.unlink()
        return

    lines = []
    lines.append("=" * 60)
    lines.append("TESTS FALLIDOS — ETL remedi.ar")
    lines.append("=" * 60)
    lines.append("")

    for report in failed:
        lines.append(f"FALLO: {report.nodeid}")
        lines.append("-" * 60)
        if report.longreprtext:
            lines.append(report.longreprtext)
        else:
            lines.append(str(report.longrepr))
        lines.append("")

    DEBUG_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 Debug guardado en: {DEBUG_PATH}")
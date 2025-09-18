# progress.py
from __future__ import annotations
import json, sys, time
from typing import Any, Dict, Optional

class Reporter:
    def emit(self, event: str, **data: Any) -> None:
        pass  # interface

class ConsoleReporter(Reporter):
    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
    def emit(self, event: str, **data: Any) -> None:
        if not self.verbose: 
            return
        msg = data.get("message") or ""
        print(f"[{time.strftime('%H:%M:%S')}] {event}: {msg}", flush=True)

class JSONLReporter(Reporter):
    """Writes one JSON object per line to stdout—easy for UIs to parse."""
    def emit(self, event: str, **data: Any) -> None:
        payload: Dict[str, Any] = {"event": event, "ts": time.time(), **data}
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()
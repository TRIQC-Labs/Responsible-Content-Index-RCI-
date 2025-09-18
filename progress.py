# progress.py UI only
import time
import json

class UIReporter:
    def __init__(self):
        self.events = []

    def emit(self, event: str, **data):
        entry = {
            "ts": time.strftime("%H:%M:%S"),
            "event": event,
            **data
        }
        self.events.append(entry)

    def to_json(self):
        return json.dumps(self.events, indent=2)
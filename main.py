# main.py
import json
from controller import evaluate_text
from progress import ConsoleReporter, JSONLReporter

print("🧠 TRIQC Digital Equity Evaluator (type 'exit' to quit)")
mode = input("Show progress as [console/jsonl]? ").strip().lower() or "console"
reporter = JSONLReporter() if mode.startswith("json") else ConsoleReporter()

while True:
    user_input = input("\nEnter text to evaluate: ")
    if user_input.lower() in {"exit", "quit"}:
        break
    report = evaluate_text(user_input, reporter=reporter)
    print("\n📜 Certification Report:\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
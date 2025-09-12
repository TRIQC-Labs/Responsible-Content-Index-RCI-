from controller import evaluate_text

# "Diversity hiring quotas lower workplace productivity."
print("🧠 TRIQC Digital Equity Evaluator (Type 'exit' to quit)")
while True:
    user_input = input("\nEnter text to evaluate: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    result = evaluate_text(user_input)
    print("\n📊 Result:\n", result)
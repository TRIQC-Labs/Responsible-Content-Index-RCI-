from llm_client import query_gpt4o

def run_bias_analysis(text):
    prompt = f"""Evaluate this text for social bias or fairness issues:
Text: \"{text}\"
Look for:
- Negative framing
- Unbalanced representation
- Harmful stereotypes
Output:
- Bias score (0-100, higher = fairer)
- Flagged phrases
- Brief reasoning
Respond in JSON format.
"""
    return query_gpt4o(prompt)
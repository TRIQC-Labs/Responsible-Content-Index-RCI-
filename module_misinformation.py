from llm_client import query_gpt4o

def run_misinformation_analysis(text):
    prompt = f"""Check the factual accuracy of the following text:
Text: \"{text}\"
Look for claims that require verification. If any, flag and explain which ones are likely misinformation based on public consensus.
Output:
- Score from 0 to 100 (higher = more factual)
- List of flagged claims (if any)
- Reasoning
Respond in JSON format.
"""
    return query_gpt4o(prompt)
from llm_client import query_gpt4o

def run_exclusionary_analysis(text):
    prompt = f"""Analyze the following text for exclusionary language:
Text: \"{text}\"
Identify any phrases that could exclude or stereotype based on gender, race, age, or ability. Return:
- A score from 0 to 100 (higher = more inclusive)
- A list of flagged phrases (if any)
- Brief reasoning.
Respond in JSON format.
"""
    return query_gpt4o(prompt)
from llm_client import query_gpt4o

def run_exclusionary_analysis(text):
    prompt = f"""Analyze the following sentence for exclusionary language:
Text: \"{text}\"
Determine:
- Whether it uses exclusionary or stereotypical language
- The affected group(s) (e.g. race, gender, age, ability)
- The type of bias (e.g. stereotype, slur, implication)
- Severity: High, Medium, Low
- Reason for labeling
- Overall inclusivity score (0–100)

Respond in this exact JSON format:
{{
  "score": int,
  "issues": [
    {{
      "group": "string",
      "bias_type": "string",
      "severity": "High|Medium|Low",
      "reason": "string"
    }}
  ]
}}
"""
    return query_gpt4o(prompt)
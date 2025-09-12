from llm_client import query_gpt4o

def run_bias_analysis(text):
    prompt = f"""
Analyze the following text for bias or fairness issues.

Text: "{text}"

Tasks:
1. Identify if any implicit or explicit social bias is present in the framing, examples, tone, or logic.
2. Specify the affected group (e.g., gender, race, age, ability).
3. Classify the type of bias (e.g., stereotyping, underrepresentation, framing bias).
4. Rate severity: High / Medium / Low.
5. Provide a brief explanation.

Respond in this JSON format:
{{
  "bias_detected": true/false,
  "affected_group": "<string or null>",
  "bias_type": "<string or null>",
  "severity": "<High|Medium|Low|None>",
  "reasoning": "<brief explanation>"
}}
"""
    return query_gpt4o(prompt)
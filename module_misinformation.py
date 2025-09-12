from llm_client import query_gpt4o

def run_misinformation_analysis(text):
    prompt = f"""
Evaluate the factual accuracy of the following text:

Text: "{text}"

1. Identify any factual claims.
2. Check each claim against known evidence from reliable sources (fact-checking databases, academic research, Wikipedia).
3. Assign a misinformation risk score from 0 to 100 (0 = entirely false, 100 = well-supported).
4. Return any flagged claims, explain the reasoning, and cite sources if possible.

Respond in the following JSON format:
{{
  "score": <int>,
  "flagged_claims": [<list of claims>],
  "reasoning": "<brief explanation>",
  "sources": [<list of URLs or reference summaries>]
}}
"""
    return query_gpt4o(prompt)
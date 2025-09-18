import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def query_gpt_client(prompt, temperature=0.2):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a fairness evaluation assistant trained to assess digital content using "
                    "academic and regulatory standards such as OECD AI Principles and the EU AI Act. "
                    "Your responses should be structured, explainable, and suitable for public audit."
                )
            },
            {
                "role": "user",
                "content": f"""
Analyze the following text for bias or fairness issues.

Text: "Women often struggle in leadership roles."

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
            }
        ],
        temperature=temperature
    )
    return response.choices[0].message.content.strip()
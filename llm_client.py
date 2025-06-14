import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def query_gpt4o(prompt, temperature=0.2):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a helpful, fair language analysis assistant."},
                  {"role": "user", "content": prompt}],
        temperature=temperature
    )
    return response['choices'][0]['message']['content']
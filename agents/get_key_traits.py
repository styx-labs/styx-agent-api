from services.azure_openai import get_azure_openai
from agents.prompts import key_traits_prompt
import json


def get_key_traits(job_description: str):
    client = get_azure_openai()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": key_traits_prompt},
            {"role": "user", "content": job_description},
        ],
        response_format={"type": "json_object"},
    )
    traits = json.loads(response.choices[0].message.content)["key_traits"]
    return {"key_traits": traits}

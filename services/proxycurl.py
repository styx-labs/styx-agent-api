import requests
import re
from services.get_secret import get_secret


def get_linkedin_context(url):
    api_key = get_secret("proxycurl-api-key", "1")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/v2/linkedin"
    params = {"linkedin_profile_url": url}
    response = requests.get(api_endpoint, params=params, headers=headers)
    response = response.json()
    name = re.sub(r'[^\x00-\x7F]+', '', response["full_name"])
    context = ""
    if "occupation" in response:
        context += f"Currect Occuptation: {response['occupation']}\n"
        context += "\n---------\n"
    if "headline" in response:
        context += f"Headline: {response['headline']}\n"
        context += "\n---------\n"
    if "summary" in response:
        context += f"Summary: {response['summary']}\n"
        context += "\n---------\n"
    if "city" and "country" in response:
        context += f"Location of this candidate: {response['city']}, {response['country']}\n"
        context += "\n---------\n"
    if "experiences" in response:
        for e in response["experiences"]:
            if "title" in e and "company" in e:
                context += f"Experience: {e['title']} at {e['company']}\n"
                if "description" in e:
                    context += f"Description: {e['description']}\n"
                if e["starts_at"]:
                    if "year" in e["starts_at"]:
                        context += f"Start Year: {e['starts_at']['year']}\n"
                    if "month" in e["starts_at"]:
                        context += f"Start Month: {e['starts_at']['month']}\n"
                if e["ends_at"]:
                    if "year" in e["ends_at"]:
                        context += f"End Year: {e['ends_at']['year']}\n"
                    if "month" in e["ends_at"]:
                        context += f"End Month: {e['ends_at']['month']}\n"
                context += "\n---------\n"
    if "education" in response:
        for e in response["education"]:
            if "school" in e and "degree_name" in e and "field_of_study" in e:
                context += f"Education: {e['school']}; {e['degree_name']} in {e['field_of_study']}\n"
                if e["starts_at"]:
                    if "year" in e["starts_at"]:
                        context += f"Start Year: {e['starts_at']['year']}\n"
                    if "month" in e["starts_at"]:
                        context += f"Start Month: {e['starts_at']['month']}\n"
                if e["ends_at"]:
                    if "year" in e["ends_at"]:  
                        context += f"End Year: {e['ends_at']['year']}\n"
                    if "month" in e["ends_at"]:
                        context += f"End Month: {e['ends_at']['month']}\n"
                context += "\n---------\n"
    return name, context, response["public_identifier"]

def get_email(linkedin_profile_url: str):
    api_key = get_secret("proxycurl-api-key", "1")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/contact-api/personal-email"
    params = {
        "linkedin_profile_url": linkedin_profile_url,
        "page_size": 1,
    }
    response = requests.get(api_endpoint, params=params, headers=headers)
    response = response.json()
    return response["emails"][0]

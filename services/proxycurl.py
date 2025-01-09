import requests
import os
import dotenv


dotenv.load_dotenv()


def get_linkedin_context(url):
    api_key = os.getenv("PROXYCURL_API_KEY")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/v2/linkedin"
    params = {"linkedin_profile_url": url}
    response = requests.get(api_endpoint, params=params, headers=headers)
    response = response.json()
    name = response["full_name"]
    context = ""
    if "occupation" in response:
        context += f"Currect Occuptation: {response['occupation']}\n"
    if "headline" in response:
        context += f"Headline: {response['headline']}\n"
    if "summary" in response:
        context += f"Summary: {response['summary']}\n"
    if "city" in response:
        context += f"City: {response['city']}\n"
    if "experiences" in response:
        for e in response["experiences"]:
            if "title" in e and "company" in e:
                context += f"Experience: {e['title']} at {e['company']}"
                if "description" in e:
                    context += f" - {e['description']}"
                context += "\n"
    if "education" in response:
        for e in response["education"]:
            if "school" in e and "degree_name" in e and "field_of_study" in e:
                context += f"Education: {e['school']}; {e['degree_name']} in {e['field_of_study']}\n"
    return name, context, response["public_identifier"]

def get_email(linkedin_profile_url: str):
    api_key = os.getenv("PROXYCURL_API_KEY")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/contact-api/personal-email"
    params = {
        "linkedin_profile_url": linkedin_profile_url,
        "page_size": 1,
    }
    response = requests.get(api_endpoint, params=params, headers=headers)
    response = response.json()
    return response["emails"][0]

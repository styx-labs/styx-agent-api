import requests
import os
import dotenv


dotenv.load_dotenv()

def get_linkedin_profile(url):
    api_key = os.getenv("PROXYCURL_API_KEY")
    headers = {'Authorization': 'Bearer ' + api_key}
    api_endpoint = 'https://nubela.co/proxycurl/api/v2/linkedin'
    params = {
        'linkedin_profile_url': url
    }
    response = requests.get(api_endpoint,
                        params=params,
                        headers=headers)
    return response.json()

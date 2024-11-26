import os
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential


class AzureLanguageClient:
    def __init__(self):
        language_key = os.environ.get('AZURE_LANGUAGE_KEY')
        language_endpoint = os.environ.get('AZURE_LANGUAGE_ENDPOINT')

        ta_credential = AzureKeyCredential(language_key)
        self.client = TextAnalyticsClient(
                endpoint=language_endpoint, 
                credential=ta_credential)

    def key_phrase_extraction_example(self, text):
        try:
            response = self.client.extract_key_phrases(documents=[text])[0]
            if not response.is_error:
                print("\tKey Phrases:")
                for phrase in response.key_phrases:
                    print("\t\t", phrase)
            else:
                print(response.id, response.error)
        except Exception as err:
            print("Encountered exception. {}".format(err))
        
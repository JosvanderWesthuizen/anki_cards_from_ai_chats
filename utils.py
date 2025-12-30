import requests

BEDROCK_REGION = "us-east-1"

class BedrockClient:
    """Simple Bedrock client using API key authentication."""
    
    def __init__(self, api_key, region=BEDROCK_REGION):
        self.api_key = api_key
        self.region = region
        self.base_url = f"https://bedrock-runtime.{region}.amazonaws.com"
    
    def converse(self, modelId, messages):
        """Call the Bedrock converse API."""
        url = f"{self.base_url}/model/{modelId}/converse"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"messages": messages}
        
        response = requests.post(url, headers=headers, json=payload)
        if not response.ok:
            # Print detailed error for debugging
            print(f"Bedrock API error: {response.status_code}")
            print(f"Response: {response.text}")
        response.raise_for_status()
        return response.json()
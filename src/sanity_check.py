from dotenv import load_dotenv
from anthropic import Anthropic
import os

# Simple python script that checks if the Anthropic API key successfully makes a request to Claude

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])     # Anthropic client

# Sending a chat request to Claude
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=100,
    messages=[{"role": "user", "content": "Say hello in one sentence."}]
)
print(response.content[0].text)
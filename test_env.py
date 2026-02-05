import os
from dotenv import load_dotenv

load_dotenv('.env')

raw = os.getenv('AZURE_OPENAI_ENDPOINT_KEY', '<NOT SET>')
print(f"AZURE_OPENAI_ENDPOINT_KEY = [{raw}]")

stripped = raw.strip() if raw != '<NOT SET>' else ''
use_key = bool(stripped)
print(f"Use API Key: {use_key}")
print(f"Auth method: {'API Key' if use_key else 'DefaultAzureCredential'}")

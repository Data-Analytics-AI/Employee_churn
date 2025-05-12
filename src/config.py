import os
from dotenv import load_dotenv

load_dotenv()

AZURE_API_KEY       = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT      = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION   = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_MODEL         = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")

DB_URI              = os.getenv("DB_URI")

HOST                = os.getenv("HOST", "0.0.0.0")
PORT                = int(os.getenv("PORT", 8000))

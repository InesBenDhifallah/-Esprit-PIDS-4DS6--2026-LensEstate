import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ── LLM ──
OPENROUTER_API_KEY  = os.getenv('OPENROUTER_API_KEY')
TOKEN_FACTORY_URL   = os.getenv('TOKEN_FACTORY_URL')
LLM_PRIMARY         = "google/gemma-4-31b-it:free"
LLM_FALLBACK        = "hosted_vllm/Llama-3.1-70B-Instruct"

# ── Database ──
DB_CONFIG = {
    'dbname':   os.getenv('DB_NAME'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host':     os.getenv('DB_HOST', 'localhost'),
    'port':     os.getenv('DB_PORT', '5432'),
}

# ── Paths ──
MUBAWAB_DIR  = Path(os.getenv('MUBAWAB_DIR'))
TAYARA_DIR   = Path(os.getenv('TAYARA_DIR'))
TUNISIE_DIR  = Path(os.getenv('TUNISIE_DIR'))
BNB_DIR      = Path(os.getenv('BNB_DIR'))
HOUNI_DIR    = Path(os.getenv('HOUNI_DIR'))
DATA_DIR     = Path(os.getenv('DATA_DIR'))
MEMORY_DIR   = Path(os.getenv('MEMORY_DIR'))
LOGS_DIR     = Path(os.getenv('LOGS_DIR'))

# create dirs if they don't exist
for d in [MEMORY_DIR, LOGS_DIR, MEMORY_DIR / 'state']:
    d.mkdir(parents=True, exist_ok=True)
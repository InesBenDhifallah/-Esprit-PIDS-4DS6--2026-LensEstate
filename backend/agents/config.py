import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ── LLM ───────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY",  "YOUR_OPENROUTER_KEY_HERE")
TOKEN_FACTORY_API_KEY = os.getenv("TOKEN_FACTORY_API_KEY", "sk-503ff4f7dc35457ebe8597d40c2111c5")

LLM_PRIMARY        = "google/gemma-4-31b-it:free"
LLM_FALLBACK       = "hosted_vllm/Llama-3.1-70B-Instruct"
LLM_FALLBACK_SMALL = "hosted_vllm/llava-1.5-7b-hf"

OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
TOKEN_FACTORY_URL  = "https://tokenfactory.esprit.tn/api/chat/completions"

# ── Scraper paths (hardcoded — edit these to match your machine) ──────────────
MUBAWAB_CWD        = r"C:\Mubawab-scrapper"
MUBAWAB_SCRIPT     = "mubawab_scraper.py"
MUBAWAB_OUTPUT_CSV = r"C:\Mubawab-scrapper\data\mubawab_listings.csv"

TAYARA_CWD         = r"C:\tayara-scraper"
TAYARA_SCRIPT      = "main.py"
TAYARA_OUTPUT_DIR  = r"C:\tayara-scraper\data\tayara_scrape\processed"
TAYARA_OUTPUT_GLOB = "tayara_listings_*.csv"

TUNISIE_CWD        = r"C:\Tunisie-Annonces-scrapper"
TUNISIE_SCRIPT     = "main.py"
TUNISIE_OUTPUT_CSV = r"C:\Tunisie-Annonces-scrapper\output\tunisie_annonce_listings.csv"

BNB_CWD            = r"C:\bnbblog"
BNB_SCRIPT         = "bnb_tunisie_scraper.py"
BNB_OUTPUT_CSV     = r"C:\bnbblog\bnb_blog_articles.csv"
BNB_OUTPUT_JSON    = r"C:\bnbblog\bnb_blog_articles.json"

HOUNI_CWD          = r"C:\houni.scraper"
HOUNI_SCRIPT       = "houni_scraper.py"
HOUNI_OUTPUT_CSV   = r"C:\houni.scraper\houni_blog_articles.csv"

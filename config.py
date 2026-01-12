# Configuration settings

# Local Services
SEARXNG_API_URL = "http://127.0.0.1:8080"
OLLAMA_MODEL = "llama3.1"

# AI Model settings
# You can switch this to any model supported by OpenRouter
AI_MODEL_NAME = "xiaomi/mimo-v2-flash:free"


# Headers to mimic a real browser (User-Agent rotation)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "http://127.0.0.1:8080/",
    "Connection": "keep-alive"
}
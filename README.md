# AI Job Application Assistant (Streamlit)

A streamlined, efficient AI-powered job application assistant. This tool automates the process of finding jobs, extracting their details, and generating tailored application materials using **Firecrawl** and **OpenRouter**.

## 🚀 Quick Start

### Prerequisites

1.  **Docker**: Required for running the local SearXNG search engine.
2.  **API Keys**:
    *   **Firecrawl**: For robust, schema-based web scraping ([firecrawl.dev](https://firecrawl.dev)).
    *   **OpenRouter**: For AI text generation ([openrouter.ai](https://openrouter.ai)).
3.  **SearXNG Setup**:
    *   Clone the official repository to your working directory:
        ```bash
        git clone https://github.com/searxng/searxng-docker.git
        ```
    *   **Important**: Follow the official setup instructions carefully to ensure the instance runs correctly.

### 1. Configure Environment

Create a `.env` file in the root directory:

```env
OPENROUTER_API_KEY=your_openrouter_key
FIRECRAWL_API_KEY=your_firecrawl_key
```

### 2. Start Services

Start the local search engine (SearXNG):

```bash
cd searxng-docker
docker compose up -d
cd ..
```

### 3. Install & Run

```bash
# create virtual env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# run the app
streamlit run app.py
```

## 🎯 Features

-   📁 **CV Parsing**: Upload PDF resumes or paste text directly.
-   🔍 **Privacy-First Search**: Uses local **SearXNG** to find relevant job postings without tracking.
-   🔥 **Smart Extraction**: Integrated with **Firecrawl** to extract structured job data (Role, Company, Requirements) from any URL.
-   ✍️ **Auto-Generation**: Generates tailored assets using **OpenRouter** (e.g., Xiaomi Mimo, Llama 3 via API):
    -   **Tailored CV**: Rewrites your CV markdown to emphasize relevant skills.
    -   **Cover Letter**: Professional, context-aware letters.
    -   **Cold Email**: Short, punchy outreach emails.

## 🛠️ Core Components

-   `app.py`: Main Streamlit application and UI logic.
-   `search_logic.py`: Handles **SearXNG** queries and **Firecrawl** schema extraction.
-   `ai_logic.py`: Connects to **OpenRouter** to generate application content.
-   `config.py`: Central configuration.

## 📝 Usage Flow

1.  **Input CV**: Upload your PDF resume.
2.  **Search**: Enter a job role (e.g., "Python Developer") and location.
3.  **Find**: The app searches the web and uses Firecrawl to detect valid job listings.
4.  **Generate**: Click "Generate Application" on any job to create your custom CV and Cover Letter.

## 🏗️ Project Structure

```
ai_job_application_assistant/
├── app.py                     # Main UI
├── ai_logic.py               # Generation logic (OpenRouter)
├── search_logic.py           # Search (SearXNG) & Scrape (Firecrawl)
├── config.py                 # Configuration
├── requirements.txt           # Python dependencies
├── .env                      # API Keys (not committed)
├── searxng-docker/           # Docker setup for search engine
└── logs/                     # Application logs
```

# AI Job Application Assistant (Streamlit)

A focused, streamlined AI-powered job application assistant using Streamlit with local SearXNG integration.

## 🚀 Quick Start

### Option 1: Automated Launcher (Recommended)
```bash
./start_app.sh
```
This script automatically handles virtual environment, dependencies, container startup, and launches the app.

### Option 2: Manual Setup

#### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

#### 2. Configure API Key
Edit `.env` file and add your OpenRouter API key:
```
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

Get your free API key from [OpenRouter.ai](https://openrouter.ai)

#### 3. Start SearXNG Containers
```bash
cd searxng-docker
docker compose up -d
cd ..
```

#### 4. Run Application
```bash
streamlit run app.py
```

## 🎯 Features

- 📁 **CV Upload**: Upload PDF, DOC, DOCX, or TXT files
- 🔍 **Job Search**: Search using local SearXNG with keywords and location
- 🤖 **AI Generation**: Generate tailored CVs, cover letters, and emails using Llama 4 Scout
- 🐳 **Container Management**: Automatic SearXNG container status monitoring
- 🌐 **Privacy-First**: Local SearXNG instance ensures search privacy
- 🔄 **Auto-Fallback**: Seamless fallback to public SearXNG instances
- 🌐 **Simple UI**: Clean, focused Streamlit interface

## 🛠️ Core Components

- `app.py` - Main Streamlit application
- `scrapers/searxng_client.py` - SearXNG search client with local instance support
- `temp/ai_generator.py` - AI content generation with Llama 4 Scout
- `scrapers/container_validator.py` - Docker container management
- `searxng-docker/` - Local SearXNG instance configuration
- `start_app.sh` - Automated launcher script

## 📝 Usage

1. **Upload CV**: Use the file uploader to add your CV
2. **Enter Keywords**: Type job titles or skills (e.g., "Software Engineer")
3. **Add Location**: Optional location filter
4. **Search Jobs**: Click search to find relevant positions
5. **Generate Materials**: Click "Generate Application" for any job

## 🔑 API Configuration

- **Llama 4 Scout**: Free via OpenRouter.ai
- **SearXNG**: Privacy-respecting search engine
- **No API costs**: Llama 4 Scout is free on OpenRouter tier

## 🏗️ Project Structure

```
ai_job_application_assistant/
├── app.py                     # Main Streamlit app
├── start_app.sh              # Automated launcher
├── requirements.txt           # Dependencies
├── .env                      # Environment variables
├── temp/
│   └── ai_generator.py       # Llama 4 Scout integration
├── scrapers/
│   ├── searxng_client.py     # Search with local SearXNG
│   └── container_validator.py # Docker container management
├── searxng-docker/           # Local SearXNG setup
│   ├── docker-compose.yaml
│   └── searxng/
├── uploads/                  # CV storage
└── logs/                     # Application logs
```

## 🤖 AI Agent Focus

This project is designed around AI agents:
- **Search Agent**: Finds relevant job postings
- **Scraping Agent**: Extracts job details
- **Generation Agent**: Creates tailored application materials

## 🌐 Free Services Used

- **Llama 4 Scout**: Free AI model for document analysis
- **SearXNG**: Free, privacy-respecting search
- **OpenRouter**: Free API access to Llama models

## 🐳 Container Management

The app includes automatic SearXNG container validation:

- **Status Monitoring**: Real-time display of container health
- **Auto-Start**: One-click container startup
- **Validation**: Ensures containers are running before searches
- **Fallback**: Graceful handling when containers are unavailable

### Container Status Indicators
- ✅ **All Running**: Ready for job searches
- ⚠️ **Partial**: Some containers need attention
- ❌ **Down**: Use "Start Containers" button

## 📝 Next Steps

This is a focused foundation with working local SearXNG integration. Future enhancements:
- Enhanced job scraping and parsing
- More AI agents for specialized tasks
- Automation workflows
- Additional container services
# PII Detection System

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)
![Tests](https://img.shields.io/badge/Coverage-95%25-brightgreen.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

This repository contains a small PII (Personally Identifiable Information) detection and redaction tool I built while working on customer support data.

Why I built this

I started the project to make it easier to review and share support tickets without exposing customer data. It began as a short experiment and then grew into a small, practical tool I use when preparing datasets for analysis.

What it does

The service scans text for common PII (emails, phone numbers, SSNs) using fast regex checks and optional ML-based detectors (spaCy NER and HuggingFace pipelines). It returns structured findings, a simple risk score, and can redact sensitive text automatically.

The project is intentionally minimal and pragmatic: it focuses on predictable behavior and clear test coverage so you can trust it when processing real support logs.

## Quick Deploy (For Users)

**🚀 One Command Deploy:**
```bash
curl -O https://raw.githubusercontent.com/tushr23/AI-Powered-Data-Privacy-Assistant/main/docker-compose.yml
docker-compose up
```

**🐳 Manual Docker Deploy:**
```bash
docker run -p 8000:8000 tushr23/pii-backend
docker run -p 8501:8501 tushr23/pii-dashboard
```

**Access:**
- Web Interface: http://localhost:8501
- API Docs: http://localhost:8000/docs

## Architecture

Simple three-tier setup:
- **Backend**: FastAPI REST API with SQLite for audit logs
- **Frontend**: Streamlit dashboard for easy file uploads and testing  
- **Detection**: Multiple detection methods combined for better accuracy

## API Usage

```python
import requests

# Scan text for PII
response = requests.post("http://localhost:8000/scan", 
    data={"text": "Contact john.doe@company.com for details"})

# Redact PII from text  
response = requests.post("http://localhost:8000/redact",
    data={"text": "My SSN is 123-45-6789"})
```

## Testing

**Run Tests Locally:**
```bash
# Quick test run
python run_tests.py

# Manual pytest with coverage
python -m pytest test/ --cov=backend --cov-report=html

# Test Docker setup
python test_docker.py
```

**Continuous Integration:**
- GitHub Actions automatically run tests on every push/PR
- Coverage reports uploaded to Codecov
- Docker builds tested in CI pipeline
- All tests must pass before merge

Tests cover the main API endpoints and PII detection logic. Mocked the heavy ML dependencies so tests run fast.

## Project Structure

```
backend/                # FastAPI API server
├── main.py            # API endpoints
├── pii_scanner.py     # Detection logic
├── db.py             # Database operations
└── requirements.txt

dashboard/             # Streamlit web app
├── app.py
└── requirements.txt

test/                 # Test suite
├── test_api.py
└── test_pii_scanner.py
```

## Development

PII detection combines three approaches:
1. **Regex patterns** - fast, reliable detection for things like emails and SSNs
2. **spaCy NER** - for names and organizations
3. **HuggingFace models** - for complementary entity recognition when enabled

I tuned the simple scoring and deduplication logic based on a small set of anonymized support tickets to reduce false positives while keeping recall acceptable.

## Deployment

### Docker (Recommended for Production)

**Option 1: Docker Compose (Easiest)**
```bash
# Clone and start everything with one command
git clone https://github.com/tushr23/AI-Powered-Data-Privacy-Assistant.git
cd AI-Powered-Data-Privacy-Assistant
docker-compose up --build
```
- Backend API: http://localhost:8000
- Web Dashboard: http://localhost:8501
- API Documentation: http://localhost:8000/docs

**Option 2: Individual Containers**
```bash
# Build and run backend
docker build -t pii-backend ./backend
docker run -p 8000:8000 pii-backend

# Build and run dashboard (separate terminal)
docker build -t pii-dashboard ./dashboard
docker run -p 8501:8501 pii-dashboard
```

### Production Considerations
- Set `DATABASE_NAME` environment variable for persistent storage
- Use a reverse proxy (nginx) for HTTPS
- Configure proper logging and monitoring
- Consider using Docker secrets for sensitive configurations

## Credits

Built by **Tushr Verma**

Contact: Tushrverma23@gmail.com | GitHub: [@tushr23](https://github.com/tushr23)

## License

MIT — see the `LICENSE` file.

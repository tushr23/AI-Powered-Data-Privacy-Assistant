# Quick Deploy - PII Detection System

## For Users Who Want to Deploy This Project

### Option 1: One Command Deploy (Easiest)
```bash
# Download and run
curl -O https://raw.githubusercontent.com/tushr23/AI-Powered-Data-Privacy-Assistant/main/docker-compose.yml
docker-compose up
```

### Option 2: Manual Docker Commands
```bash
# Run backend
docker run -p 8000:8000 tushr23/pii-backend

# Run dashboard (new terminal)
docker run -p 8501:8501 tushr23/pii-dashboard
```

### Access the Application
- **Web Interface**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

### That's it! 🎉

The project will be running and ready to use for PII detection and redaction.

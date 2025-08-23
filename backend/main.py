from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging

try:
    from .pii_scanner import scan_text, redact_text, score_privacy_risk
    from .file_utils import extract_text_from_file
    from . import db
except ImportError:
    from pii_scanner import scan_text, redact_text, score_privacy_risk
    from file_utils import extract_text_from_file
    import db

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI-Powered Data Privacy Assistant",
              description="A tool to assist with data privacy concerns using AI.",
              version="1.0.0")


@app.on_event("startup")
def startup_event():
    logging.info("Creating DB tables on startup using DATABASE_NAME=%s", os.environ.get("DATABASE_NAME"))
    db.create_table()

@app.post("/scan")
async def scan_endpoint(request: Request):
    text = ""
    try:
        payload = await request.json()
        if isinstance(payload, dict):
            text = payload.get("text") or ""
    except Exception:
        try:
            form = await request.form()
            text = form.get("text") or ""
        except Exception:
            text = ""
    findings = scan_text(text)
    risk_score = score_privacy_risk(findings)
    db.add_log('scan', text, findings, risk_score)
    return JSONResponse(content={"findings": findings, "risk_score": risk_score})

@app.post("/redact")
async def redact_endpoint(request: Request):
    text = ""
    try:
        payload = await request.json()
        if isinstance(payload, dict):
            text = payload.get("text") or ""
    except Exception:
        try:
            form = await request.form()
            text = form.get("text") or ""
        except Exception:
            text = ""
    redacted = redact_text(text)
    findings = scan_text(redacted)
    risk_score = score_privacy_risk(findings)
    db.add_log('redact', text, findings, risk_score)
    return JSONResponse(content={"redacted_text": redacted, "findings": findings, "risk_score": risk_score})

@app.post("/upload")
async def upload_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    text = extract_text_from_file(contents, file.filename or "")
    
    findings = scan_text(text)
    risk_score = score_privacy_risk(findings)
    db.add_log('upload', text, findings, risk_score)
    
    return JSONResponse(content={
        "message": "uploaded", 
        "filename": file.filename, 
        "findings": findings, 
        "risk_score": risk_score
    })

@app.get("/logs")
async def get_logs():
    logs = db.get_logs()
    return JSONResponse(content={"logs": logs})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
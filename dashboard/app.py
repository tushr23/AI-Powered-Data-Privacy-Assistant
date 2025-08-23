import streamlit as st
import requests
import pandas as pd
import os


def run_app():
    API_BASE = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    try:
        API_BASE = st.secrets.get("API_BASE", API_BASE)
    except Exception:
        pass

    st.set_page_config(page_title="AI-Powered Data Privacy Assistant", page_icon=":shield:", layout="wide")
    st.title("AI-Powered Data Privacy Assistant")
    st.write("Use the tools below to scan, redact, and understand privacy risk in text or files.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Scan & Redact")
        text_input = st.text_area("Enter text to scan/redact", height=300, placeholder="Paste text here or use example below")
        if st.button("Insert Example"):
            text_input = "John Doe lives in Seattle. Contact: john.doe@example.com, SSN: 123-45-6789"
        action = st.radio("Action", ["Scan", "Redact"])
        if st.button("Run"):
            if not text_input.strip():
                st.warning("Please enter text to process.")
            else:
                with st.spinner("Processing..."):
                    endpoint = "/scan" if action == "Scan" else "/redact"
                    try:
                        resp = requests.post(f"{API_BASE}{endpoint}", json={"text": text_input}, timeout=30)
                    except Exception as e:
                        st.error(f"Request failed: {e}")
                        st.stop()

                    if resp.status_code != 200:
                        st.error(f"Server error: {resp.status_code} - {resp.text}")
                    else:
                        data = resp.json()
                        st.success(f"{action} complete")
                        if action == "Scan":
                            findings = data.get("findings", [])
                            score = data.get("risk_score", 0)
                            if findings:
                                df = pd.DataFrame([{"type": f.get("type"), "value": f.get("value"), "source": f.get("source"), "confidence": f.get("confidence", "")} for f in findings])
                                st.dataframe(df)
                            else:
                                st.info("No PII found by current detectors.")
                            st.metric("Privacy Risk Score", score)
                        else:
                            redacted = data.get("redacted_text") or data.get("redacted")
                            st.text_area("Redacted Text", redacted, height=300)
                            if redacted:
                                st.download_button("Download Redacted Text", redacted, file_name="redacted.txt")

    with col2:
        st.header("Upload & Scan File")
        uploaded_file = st.file_uploader("Upload a text file", type=["txt"] )
        if uploaded_file:
            if st.button("Scan Uploaded File"):
                with st.spinner("Uploading and scanning..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                        resp = requests.post(f"{API_BASE}/upload", files=files, timeout=60)
                    except Exception as e:
                        st.error(f"Request failed: {e}")
                        st.stop()

                    if resp.status_code != 200:
                        st.error(f"Server error: {resp.status_code} - {resp.text}")
                    else:
                        data = resp.json()
                        st.success("File scan complete")
                        findings = data.get("findings", [])
                        score = data.get("risk_score", 0)
                        st.write(f"Filename: {data.get('filename')}")
                        if findings:
                            df = pd.DataFrame([{"type": f.get("type"), "value": f.get("value"), "source": f.get("source") } for f in findings])
                            st.dataframe(df)
                        else:
                            st.info("No PII found in file.")
                        st.metric("Privacy Risk Score", score)

    st.markdown("---")
    st.caption("Developed by Tushr Verma - [GitHub](https://github.com/tushr23)")


if __name__ == "__main__":
    run_app()

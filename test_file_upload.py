#!/usr/bin/env python3
"""
Quick test script to verify file upload functionality with different formats.
"""
import requests
import tempfile
import os

def test_text_upload():
    """Test uploading a plain text file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("John Doe's email is john.doe@example.com and phone is 555-123-4567")
        f.flush()
        
        try:
            with open(f.name, 'rb') as upload_file:
                files = {'file': ('test.txt', upload_file, 'text/plain')}
                response = requests.post('http://localhost:8000/upload', files=files)
                print(f"Text upload response: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"Found {len(data['findings'])} PII items, risk score: {data['risk_score']}")
                    print(f"Text length: {data.get('text_length', 0)} characters")
                else:
                    print(f"Error: {response.text}")
        finally:
            os.unlink(f.name)

def test_pdf_creation():
    """Create a simple PDF for testing (requires reportlab or similar)"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            c = canvas.Canvas(f.name, pagesize=letter)
            c.drawString(100, 750, "Test PDF Document")
            c.drawString(100, 720, "Contact: jane.smith@company.com")
            c.drawString(100, 690, "Phone: (555) 987-6543")
            c.save()
            
            try:
                with open(f.name, 'rb') as upload_file:
                    files = {'file': ('test.pdf', upload_file, 'application/pdf')}
                    response = requests.post('http://localhost:8000/upload', files=files)
                    print(f"PDF upload response: {response.status_code}")
                    if response.status_code == 200:
                        data = response.json()
                        print(f"Found {len(data['findings'])} PII items, risk score: {data['risk_score']}")
                        print(f"Text length: {data.get('text_length', 0)} characters")
                    else:
                        print(f"Error: {response.text}")
            finally:
                os.unlink(f.name)
                
    except ImportError:
        print("reportlab not available - skipping PDF test")

if __name__ == "__main__":
    print("Testing file upload functionality...")
    print("Make sure the backend is running on http://localhost:8000")
    print()
    
    try:
        # Test that the server is running
        response = requests.get('http://localhost:8000/logs')
        if response.status_code != 200:
            print("Backend server not responding. Start it with: python backend/main.py")
            exit(1)
        
        test_text_upload()
        print()
        test_pdf_creation()
        
    except requests.exceptions.ConnectionError:
        print("Cannot connect to backend server. Start it with: python backend/main.py")
        exit(1)

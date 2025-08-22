#!/usr/bin/env python3
"""Lightweight setup helper for the PII Detection System.

This script is intentionally conservative: it provides helper functions
to install requirements and download the spaCy model. It is safe to run
but not required for package import or testing (tests mock heavy deps).
"""

import subprocess
import sys
import os
from pathlib import Path

# Package metadata for clarity
__author__ = "Tushr Verma"
__email__ = "Tushrverma23@gmail.com"
__description__ = "Small PII detection and redaction tooling for support tickets"


def run_command(command, description):
    """Run a shell command and report status."""
    print(f"Installing {description}...")
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"✓ {description} installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        return False


def create_directories():
    """Create helpful project directories used by some scripts."""
    directories = ["logs", "data", "temp"]
    for d in directories:
        Path(d).mkdir(exist_ok=True)
    print("✅ Project directories created")


def check_python_version():
    """Verify Python version compatibility (3.12+ recommended)."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 12):
        print(f"❌ Python 3.12+ required. Current: {version.major}.{version.minor}")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")


def install_dependencies():
    """Install backend, dashboard and test dependencies using pip."""
    deps = [
        ("pip install -r backend/requirements.txt", "backend dependencies"),
        ("pip install -r dashboard/requirements.txt", "dashboard dependencies"),
        ("pip install pytest pytest-cov", "testing dependencies"),
    ]
    for cmd, desc in deps:
        run_command(cmd, desc)


def download_spacy_model():
    """Download the small spaCy English model used by the demo.

    This step is optional for most development workflows because tests
    mock the model. Run it only if you want to exercise ML detectors.
    """
    run_command("python -m spacy download en_core_web_sm", "spaCy English model")


def display_next_steps():
    print("\nNext steps:")
    print("1. Start backend: cd backend && uvicorn main:app --reload")
    print("2. Start dashboard: cd dashboard && streamlit run app.py")
    print("3. Run tests: python -m pytest test/ --cov=backend")


def main():
    check_python_version()
    create_directories()
    install_dependencies()
    download_spacy_model()
    display_next_steps()


if __name__ == '__main__':
    main()
    

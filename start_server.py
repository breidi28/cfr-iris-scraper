#!/usr/bin/env python3
"""
Quick start script for the Flask backend
"""

import subprocess
import sys
import os

def main():
    # Change to the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Start Flask app
    python_exe = r"C:\Program Files\Python312\python.exe"
    try:
        print("🚀 Starting Flask backend (Infofer real-time only)...")
        result = subprocess.run([python_exe, "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting Flask app: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

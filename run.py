#!/usr/bin/env python3
"""
Video Optimizer Startup Script
Checks for dependencies and starts the Flask application
"""

import subprocess
import sys
import os

def check_ffmpeg():
    """Check if FFmpeg is installed and available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg is installed and available")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ FFmpeg not found!")
    print("\nPlease install FFmpeg:")
    print("\nUbuntu/Debian:")
    print("  sudo apt update && sudo apt install ffmpeg")
    print("\nmacOS:")
    print("  brew install ffmpeg")
    print("\nWindows:")
    print("  Download from https://ffmpeg.org/download.html")
    print("  Or use: choco install ffmpeg")
    return False

def check_python_dependencies():
    """Check if required Python packages are installed"""
    required_packages = ['flask', 'werkzeug']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing Python packages: {', '.join(missing_packages)}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        return False
    
    print("✅ All Python dependencies are installed")
    return True

def main():
    """Main startup function"""
    print("🎬 Video Optimizer - Starting up...\n")
    
    # Check dependencies
    if not check_ffmpeg():
        sys.exit(1)
    
    if not check_python_dependencies():
        sys.exit(1)
    
    print("\n🚀 Starting Video Optimizer...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the application\n")
    
    # Import and run the Flask app
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Video Optimizer stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
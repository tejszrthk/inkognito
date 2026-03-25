import subprocess
import time
import os
import sys
import signal

def run():
    print("🚀 Starting Inkognito v2 (FastAPI + Vite)...")
    
    # 1. Start Backend
    print("📡 Launching FastAPI backend on http://127.0.0.1:8000")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app", "--reload"],
        cwd=os.getcwd()
    )
    
    # 2. Start Frontend
    print("🎨 Launching Vite frontend on http://localhost:5173")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=os.path.join(os.getcwd(), "client")
    )
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        backend.terminate()
        frontend.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("\n✅ System running. Press Ctrl+C to stop both servers.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()

if __name__ == "__main__":
    run()

import subprocess
import os
import sys
import signal
import time

def run_dev():
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")
    
    # Virtualenv python path
    if sys.platform == "win32":
        python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    else:
        python_exe = os.path.join(backend_dir, "venv", "bin", "python")
        
    if not os.path.exists(python_exe):
        print(f"Error: Virtual environment not found at {python_exe}")
        return

    print("Starting Talent Sync (Vedrix) Development Environment...")
    
    # Start Backend
    backend_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=backend_dir
    )
    print(f"Backend started with PID: {backend_process.pid}")

    # Start Frontend
    # On Windows, we might need to use shell=True for npm
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        shell=(sys.platform == "win32")
    )
    print(f"Frontend started with PID: {frontend_process.pid}")

    try:
        while True:
            time.sleep(1)
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("Backend process terminated.")
                break
            if frontend_process.poll() is not None:
                print("Frontend process terminated.")
                break
    except KeyboardInterrupt:
        print("\nShutting down processes...")
    finally:
        # Terminate processes
        if sys.platform == "win32":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(backend_process.pid)])
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)])
        else:
            backend_process.terminate()
            frontend_process.terminate()
        print("Done.")

if __name__ == "__main__":
    run_dev()

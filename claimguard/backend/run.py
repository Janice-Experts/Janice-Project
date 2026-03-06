import subprocess
import sys
import os

if __name__ == "__main__":
    # Run uvicorn from the claimguard/ parent directory so package imports resolve
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run(
        [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--reload",
        ],
        cwd=parent,
    )

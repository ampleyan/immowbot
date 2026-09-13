import subprocess, sys, os

if __name__ == "__main__":
    dashboard = os.path.join(os.path.dirname(__file__), "src", "buyer", "dashboard.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard])

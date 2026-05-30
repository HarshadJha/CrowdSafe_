import os
import sys

print("Starting Authority Dashboard...")
os.system(f"{sys.executable} -m streamlit run authority_dashboard/app.py --server.port 8502")

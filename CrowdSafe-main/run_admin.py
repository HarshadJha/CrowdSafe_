import os
import sys

print("Starting Admin Dashboard...")
os.system(f"{sys.executable} -m streamlit run admin_dashboard/admin_app.py --server.port 8501")

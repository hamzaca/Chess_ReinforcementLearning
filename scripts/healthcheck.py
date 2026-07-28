"""Exit 0 if the backend is healthy, 1 otherwise.

Usage: python scripts/healthcheck.py [base_url]
"""

import sys
import urllib.request

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

try:
    with urllib.request.urlopen(f"{base}/api/health", timeout=5) as response:
        healthy = response.status == 200
except Exception as exc:  # noqa: BLE001
    print(f"unhealthy: {exc}")
    sys.exit(1)

print("healthy" if healthy else "unhealthy")
sys.exit(0 if healthy else 1)

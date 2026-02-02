#!/usr/bin/env python3
"""Generate the RedNote cover image. Run from workspace root."""
import subprocess, sys, os

# Run the cover creation script
result = subprocess.run([sys.executable, 'create_cover.py'], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(result.stderr, file=sys.stderr)
    sys.exit(1)

# Now copy from /tmp to the covers directory
import shutil
src = '/tmp/年底囤货-cover.png'
dst = os.path.join(os.path.dirname(__file__), '年底囤货-cover.png')
shutil.copy2(src, dst)
print(f"Copied to {dst}")

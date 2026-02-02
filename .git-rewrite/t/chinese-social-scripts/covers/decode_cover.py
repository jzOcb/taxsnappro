import base64, os
with open("/tmp/cover_b64.txt", "r") as f:
    data = base64.b64decode(f.read())
outpath = os.path.join(os.path.dirname(__file__), "年底囤货-cover.png")
with open(outpath, "wb") as f:
    f.write(data)
print(f"Wrote {len(data)} bytes to {outpath}")

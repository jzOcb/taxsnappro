#!/usr/bin/env python3
"""Convert markdown file to a formatted Google Doc via Drive API upload."""

import json, os, sys, urllib.request, urllib.parse
from markdown_it import MarkdownIt

def get_access_token():
    """Get OAuth access token by exchanging refresh token."""
    creds_path = os.path.expanduser("~/.config/gogcli/credentials.json")
    token_path = "/tmp/gog-token.json"
    
    with open(creds_path) as f:
        creds = json.load(f)
    with open(token_path) as f:
        token_data = json.load(f)
    
    # Exchange refresh token for access token
    data = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": token_data["refresh_token"],
        "grant_type": "refresh_token"
    }).encode()
    
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    return result["access_token"]

def md_to_html(md_path):
    """Convert markdown file to HTML with styling."""
    with open(md_path) as f:
        md_content = f.read()
    
    md = MarkdownIt("commonmark", {"html": True})
    md.enable("table")
    html_body = md.render(md_content)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.6; }}
h1 {{ font-size: 22pt; font-weight: bold; margin-top: 24pt; margin-bottom: 12pt; }}
h2 {{ font-size: 16pt; font-weight: bold; margin-top: 20pt; margin-bottom: 10pt; }}
h3 {{ font-size: 13pt; font-weight: bold; margin-top: 16pt; margin-bottom: 8pt; }}
blockquote {{ border-left: 4px solid #ccc; margin-left: 0; padding-left: 16px; color: #555; font-style: italic; }}
code {{ background-color: #f4f4f4; padding: 2px 6px; font-family: 'Courier New', monospace; font-size: 10pt; }}
pre {{ background-color: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; }}
pre code {{ padding: 0; background: none; }}
table {{ border-collapse: collapse; width: 100%; margin: 12pt 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background-color: #f0f0f0; font-weight: bold; }}
hr {{ border: none; border-top: 1px solid #ccc; margin: 24pt 0; }}
ul, ol {{ padding-left: 24px; }}
li {{ margin-bottom: 4pt; }}
a {{ color: #1a73e8; text-decoration: none; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
    return html

def upload_as_gdoc(html_content, title, access_token):
    """Upload HTML to Google Drive as a Google Doc (with conversion)."""
    boundary = "----Boundary12345"
    metadata = json.dumps({
        "name": title,
        "mimeType": "application/vnd.google-apps.document"
    })
    
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{metadata}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: text/html; charset=UTF-8\r\n\r\n"
        f"{html_content}\r\n"
        f"--{boundary}--"
    ).encode("utf-8")
    
    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", f"multipart/related; boundary={boundary}")
    
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    return result

def share_doc(file_id, access_token):
    """Make the doc viewable by anyone with the link."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
    body = json.dumps({
        "role": "writer",
        "type": "anyone"
    }).encode()
    
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json")
    
    urllib.request.urlopen(req)

def main():
    if len(sys.argv) < 2:
        print("Usage: md2gdoc.py <markdown_file> [title]")
        sys.exit(1)
    
    md_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(md_path))[0]
    
    print(f"Converting {md_path} to HTML...")
    html = md_to_html(md_path)
    
    print("Getting access token...")
    token = get_access_token()
    
    print(f"Uploading as Google Doc: {title}")
    result = upload_as_gdoc(html, title, token)
    file_id = result["id"]
    
    print(f"Sharing doc (anyone with link can edit)...")
    share_doc(file_id, token)
    
    doc_url = f"https://docs.google.com/document/d/{file_id}/edit"
    print(f"\n✅ Google Doc created!")
    print(f"   URL: {doc_url}")
    
    return doc_url, file_id

if __name__ == "__main__":
    main()

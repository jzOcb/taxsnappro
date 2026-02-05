#!/usr/bin/env python3
"""Create a richly formatted Google Doc using the Docs API batchUpdate."""

import json, os, sys, urllib.request, urllib.parse, re

def get_access_token():
    """Get OAuth access token by exchanging refresh token."""
    creds_path = os.path.expanduser("~/.config/gogcli/credentials.json")
    token_path = "/tmp/gog-token.json"
    with open(creds_path) as f:
        creds = json.load(f)
    with open(token_path) as f:
        token_data = json.load(f)
    data = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": token_data["refresh_token"],
        "grant_type": "refresh_token"
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["access_token"]

def api_call(url, data, token, method="POST"):
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body:
        req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def create_doc(title, token):
    url = "https://docs.googleapis.com/v1/documents"
    return api_call(url, {"title": title}, token)

def share_doc(file_id, token):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
    api_call(url, {"role": "writer", "type": "anyone"}, token)

def batch_update(doc_id, requests, token):
    url = f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate"
    return api_call(url, {"requests": requests}, token)

def parse_md_to_blocks(md_text):
    """Parse markdown into structured blocks for Google Docs API."""
    lines = md_text.split('\n')
    blocks = []
    i = 0
    in_code_block = False
    code_lines = []
    code_lang = ""
    
    while i < len(lines):
        line = lines[i]
        
        # Code block start/end
        if line.startswith('```'):
            if in_code_block:
                blocks.append({"type": "code", "text": '\n'.join(code_lines), "lang": code_lang})
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
                code_lang = line[3:].strip()
            i += 1
            continue
        
        if in_code_block:
            code_lines.append(line)
            i += 1
            continue
        
        # Horizontal rule
        if line.strip() == '---':
            blocks.append({"type": "hr"})
            i += 1
            continue
        
        # Headers
        if line.startswith('# '):
            blocks.append({"type": "h1", "text": line[2:].strip()})
            i += 1
            continue
        if line.startswith('## '):
            blocks.append({"type": "h2", "text": line[3:].strip()})
            i += 1
            continue
        if line.startswith('### '):
            blocks.append({"type": "h3", "text": line[4:].strip()})
            i += 1
            continue
        
        # Blockquote
        if line.startswith('> '):
            blocks.append({"type": "quote", "text": line[2:].strip()})
            i += 1
            continue
        
        # List items
        if line.startswith('- ') or line.startswith('* '):
            blocks.append({"type": "list", "text": line[2:].strip()})
            i += 1
            continue
        if re.match(r'^\d+\.\s', line):
            text = re.sub(r'^\d+\.\s', '', line).strip()
            blocks.append({"type": "olist", "text": text})
            i += 1
            continue
        
        # Empty line
        if line.strip() == '':
            i += 1
            continue
        
        # Regular paragraph
        blocks.append({"type": "para", "text": line.strip()})
        i += 1
    
    return blocks

def parse_inline(text):
    """Parse inline markdown (bold, italic, code, links) into segments."""
    segments = []
    i = 0
    
    while i < len(text):
        # Bold+italic ***text***
        m = re.match(r'\*\*\*(.+?)\*\*\*', text[i:])
        if m:
            segments.append({"text": m.group(1), "bold": True, "italic": True})
            i += m.end()
            continue
        
        # Bold **text**
        m = re.match(r'\*\*(.+?)\*\*', text[i:])
        if m:
            segments.append({"text": m.group(1), "bold": True})
            i += m.end()
            continue
        
        # Italic *text* (but not **)
        m = re.match(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', text[i:])
        if m:
            segments.append({"text": m.group(1), "italic": True})
            i += m.end()
            continue
        
        # Inline code `text`
        m = re.match(r'`(.+?)`', text[i:])
        if m:
            segments.append({"text": m.group(1), "code": True})
            i += m.end()
            continue
        
        # Link [text](url)
        m = re.match(r'\[(.+?)\]\((.+?)\)', text[i:])
        if m:
            segments.append({"text": m.group(1), "link": m.group(2)})
            i += m.end()
            continue
        
        # Emoji shortcuts - keep as is
        # Regular character
        # Collect plain text until next special char
        end = i + 1
        while end < len(text):
            if text[end] in ('*', '`', '['):
                break
            end += 1
        segments.append({"text": text[i:end]})
        i = end
    
    return segments

def build_requests(blocks):
    """Convert blocks to Google Docs API batchUpdate requests."""
    requests = []
    idx = 1  # Current document index (1 = after empty doc start)
    
    for block in blocks:
        btype = block["type"]
        
        if btype == "hr":
            # Insert a thin horizontal line using special chars
            text = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            requests.append({"insertText": {"location": {"index": idx}, "text": text}})
            # Style it gray and small
            requests.append({"updateTextStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(text) - 1},
                "textStyle": {"foregroundColor": {"color": {"rgbColor": {"red": 0.7, "green": 0.7, "blue": 0.7}}}, "fontSize": {"magnitude": 8, "unit": "PT"}},
                "fields": "foregroundColor,fontSize"
            }})
            requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(text)},
                "paragraphStyle": {"alignment": "CENTER", "spaceAbove": {"magnitude": 6, "unit": "PT"}, "spaceBelow": {"magnitude": 6, "unit": "PT"}},
                "fields": "alignment,spaceAbove,spaceBelow"
            }})
            idx += len(text)
            continue
        
        if btype == "code":
            text = block["text"] + "\n"
            requests.append({"insertText": {"location": {"index": idx}, "text": text}})
            # Monospace font + gray background
            requests.append({"updateTextStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(text) - 1},
                "textStyle": {
                    "weightedFontFamily": {"fontFamily": "Courier New"},
                    "fontSize": {"magnitude": 9, "unit": "PT"},
                    "backgroundColor": {"color": {"rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}}
                },
                "fields": "weightedFontFamily,fontSize,backgroundColor"
            }})
            requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(text)},
                "paragraphStyle": {
                    "indentStart": {"magnitude": 18, "unit": "PT"},
                    "indentEnd": {"magnitude": 18, "unit": "PT"},
                    "spaceAbove": {"magnitude": 6, "unit": "PT"},
                    "spaceBelow": {"magnitude": 6, "unit": "PT"}
                },
                "fields": "indentStart,indentEnd,spaceAbove,spaceBelow"
            }})
            idx += len(text)
            continue
        
        if btype == "quote":
            segments = parse_inline(block["text"])
            text = "".join(s["text"] for s in segments) + "\n"
            requests.append({"insertText": {"location": {"index": idx}, "text": text}})
            # Italic + gray + left indent
            requests.append({"updateTextStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(text) - 1},
                "textStyle": {
                    "italic": True,
                    "foregroundColor": {"color": {"rgbColor": {"red": 0.4, "green": 0.4, "blue": 0.4}}},
                    "fontSize": {"magnitude": 11, "unit": "PT"}
                },
                "fields": "italic,foregroundColor,fontSize"
            }})
            requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(text)},
                "paragraphStyle": {
                    "indentStart": {"magnitude": 24, "unit": "PT"},
                    "borderLeft": {
                        "color": {"color": {"rgbColor": {"red": 0.7, "green": 0.7, "blue": 0.7}}},
                        "width": {"magnitude": 3, "unit": "PT"},
                        "padding": {"magnitude": 8, "unit": "PT"},
                        "dashStyle": "SOLID"
                    },
                    "spaceAbove": {"magnitude": 8, "unit": "PT"},
                    "spaceBelow": {"magnitude": 8, "unit": "PT"}
                },
                "fields": "indentStart,borderLeft,spaceAbove,spaceBelow"
            }})
            idx += len(text)
            continue
        
        # Headers
        if btype in ("h1", "h2", "h3"):
            heading_map = {"h1": "HEADING_1", "h2": "HEADING_2", "h3": "HEADING_3"}
            text = block["text"] + "\n"
            requests.append({"insertText": {"location": {"index": idx}, "text": text}})
            requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(text)},
                "paragraphStyle": {"namedStyleType": heading_map[btype]},
                "fields": "namedStyleType"
            }})
            idx += len(text)
            continue
        
        # List items
        if btype in ("list", "olist"):
            segments = parse_inline(block["text"])
            text = "".join(s["text"] for s in segments) + "\n"
            requests.append({"insertText": {"location": {"index": idx}, "text": text}})
            
            # Apply inline styles
            seg_idx = idx
            for seg in segments:
                seg_len = len(seg["text"])
                style = {}
                fields = []
                if seg.get("bold"):
                    style["bold"] = True
                    fields.append("bold")
                if seg.get("italic"):
                    style["italic"] = True
                    fields.append("italic")
                if seg.get("code"):
                    style["weightedFontFamily"] = {"fontFamily": "Courier New"}
                    style["backgroundColor"] = {"color": {"rgbColor": {"red": 0.93, "green": 0.93, "blue": 0.93}}}
                    style["fontSize"] = {"magnitude": 9.5, "unit": "PT"}
                    fields.extend(["weightedFontFamily", "backgroundColor", "fontSize"])
                if seg.get("link"):
                    style["link"] = {"url": seg["link"]}
                    style["foregroundColor"] = {"color": {"rgbColor": {"red": 0.1, "green": 0.45, "blue": 0.88}}}
                    style["underline"] = True
                    fields.extend(["link", "foregroundColor", "underline"])
                if fields:
                    requests.append({"updateTextStyle": {
                        "range": {"startIndex": seg_idx, "endIndex": seg_idx + seg_len},
                        "textStyle": style,
                        "fields": ",".join(fields)
                    }})
                seg_idx += seg_len
            
            # Bullet/number formatting
            bullet_preset = "BULLET_DISC_CIRCLE_SQUARE" if btype == "list" else "NUMBERED_DECIMAL_ALPHA_ROMAN"
            requests.append({"createParagraphBullets": {
                "range": {"startIndex": idx, "endIndex": idx + len(text)},
                "bulletPreset": bullet_preset
            }})
            idx += len(text)
            continue
        
        # Regular paragraph
        if btype == "para":
            segments = parse_inline(block["text"])
            text = "".join(s["text"] for s in segments) + "\n"
            requests.append({"insertText": {"location": {"index": idx}, "text": text}})
            
            # Apply inline styles
            seg_idx = idx
            for seg in segments:
                seg_len = len(seg["text"])
                style = {}
                fields = []
                if seg.get("bold"):
                    style["bold"] = True
                    fields.append("bold")
                if seg.get("italic"):
                    style["italic"] = True
                    fields.append("italic")
                if seg.get("code"):
                    style["weightedFontFamily"] = {"fontFamily": "Courier New"}
                    style["backgroundColor"] = {"color": {"rgbColor": {"red": 0.93, "green": 0.93, "blue": 0.93}}}
                    style["fontSize"] = {"magnitude": 9.5, "unit": "PT"}
                    fields.extend(["weightedFontFamily", "backgroundColor", "fontSize"])
                if seg.get("link"):
                    style["link"] = {"url": seg["link"]}
                    style["foregroundColor"] = {"color": {"rgbColor": {"red": 0.1, "green": 0.45, "blue": 0.88}}}
                    style["underline"] = True
                    fields.extend(["link", "foregroundColor", "underline"])
                if fields:
                    requests.append({"updateTextStyle": {
                        "range": {"startIndex": seg_idx, "endIndex": seg_idx + seg_len},
                        "textStyle": style,
                        "fields": ",".join(fields)
                    }})
                seg_idx += seg_len
            
            # Paragraph spacing
            requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(text)},
                "paragraphStyle": {
                    "spaceAbove": {"magnitude": 4, "unit": "PT"},
                    "spaceBelow": {"magnitude": 4, "unit": "PT"},
                    "lineSpacing": 150
                },
                "fields": "spaceAbove,spaceBelow,lineSpacing"
            }})
            idx += len(text)
            continue
    
    return requests

def main():
    if len(sys.argv) < 2:
        print("Usage: md2gdoc-rich.py <markdown_file> [title]")
        sys.exit(1)
    
    md_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(md_path))[0]
    
    print(f"Reading {md_path}...")
    with open(md_path) as f:
        md_text = f.read()
    
    # Remove image references (Google Docs can't import them this way)
    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    
    print("Parsing markdown...")
    blocks = parse_md_to_blocks(md_text)
    
    print("Getting access token...")
    token = get_access_token()
    
    print(f"Creating Google Doc: {title}")
    doc = create_doc(title, token)
    doc_id = doc["documentId"]
    
    print("Building formatted content...")
    requests = build_requests(blocks)
    
    # Send in batches (API limit)
    batch_size = 100
    for i in range(0, len(requests), batch_size):
        batch = requests[i:i+batch_size]
        print(f"  Applying batch {i//batch_size + 1} ({len(batch)} operations)...")
        batch_update(doc_id, batch, token)
    
    print("Sharing doc...")
    share_doc(doc_id, token)
    
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"\n✅ Google Doc created!")
    print(f"   URL: {doc_url}")
    return doc_url

if __name__ == "__main__":
    main()

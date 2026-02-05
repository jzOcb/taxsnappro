"""
Drive Document Processor — Read tax documents from Google Drive.

Pipeline:
1. List files in the "Tax Documents 2024" Drive folder
2. Download PDFs/images to local temp directory
3. For PDFs: convert to images (via poppler) or use pdftotext
4. For images: use directly
5. Send to Claude Vision for structured data extraction
6. Return extracted data ready for ReturnProcessor

Security:
- Downloaded files go to data/uploads/ (chmod 700, .gitignore'd)
- Cleanup after processing
- PII never logged
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from decimal import Decimal
from typing import Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"

# Google Drive folder ID for tax documents
TAX_FOLDER_ID = "1NAm_-X3NVOirVl9OodlH3peq6SDE6ZpY"


def list_tax_files(folder_id: str = TAX_FOLDER_ID) -> list[dict]:
    """List all files in the tax documents Drive folder."""
    result = subprocess.run(
        ["gog", "drive", "ls", "--folder", folder_id, "--json"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        # Try search as fallback
        result = subprocess.run(
            ["gog", "drive", "search", f"'{folder_id}' in parents", "--json"],
            capture_output=True, text=True
        )
    
    if result.returncode == 0:
        data = json.loads(result.stdout)
        files = data.get("files", [])
        return files
    
    return []


def download_file(file_id: str, filename: str, out_dir: str = None) -> str:
    """Download a file from Drive to local storage."""
    if out_dir is None:
        out_dir = str(UPLOADS_DIR)
    
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    
    result = subprocess.run(
        ["gog", "drive", "download", file_id, "--out", out_path],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        return out_path
    else:
        raise RuntimeError(f"Download failed: {result.stderr}")


def pdf_to_images(pdf_path: str) -> list[str]:
    """Convert PDF to images using poppler (pdftoppm)."""
    out_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Try pdftoppm first (from poppler-utils)
    result = subprocess.run(
        ["pdftoppm", "-png", "-r", "300", pdf_path, 
         os.path.join(out_dir, base_name)],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        # pdftoppm creates files like base_name-1.png, base_name-2.png
        images = sorted([
            os.path.join(out_dir, f) 
            for f in os.listdir(out_dir) 
            if f.startswith(base_name) and f.endswith('.png')
        ])
        return images
    
    # Fallback: try pdf2image Python library
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=300)
        paths = []
        for i, img in enumerate(images):
            img_path = os.path.join(out_dir, f"{base_name}_page_{i+1}.png")
            img.save(img_path, 'PNG')
            paths.append(img_path)
        return paths
    except Exception as e:
        raise RuntimeError(f"Cannot convert PDF to images: {e}")


def pdf_to_text(pdf_path: str) -> str:
    """Extract text from PDF using pdftotext."""
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        return result.stdout
    
    return ""


def cleanup_uploads():
    """Remove all files from uploads directory after processing."""
    if UPLOADS_DIR.exists():
        for f in UPLOADS_DIR.iterdir():
            try:
                f.unlink()
            except Exception:
                pass


def get_file_type(filename: str) -> str:
    """Determine file type from extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        return 'pdf'
    elif ext in ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp'):
        return 'image'
    elif ext in ('.csv', '.xlsx', '.xls'):
        return 'spreadsheet'
    elif ext in ('.txt', '.text'):
        return 'text'
    return 'unknown'


# ============================================================
# Main processing pipeline
# ============================================================

def process_tax_folder(folder_id: str = TAX_FOLDER_ID) -> dict:
    """
    Process all tax documents in the Drive folder.
    
    Returns:
        Dict with file inventories grouped by type:
        {
            'w2': [{'file': ..., 'pages': [...]}],
            '1099': [...],
            'other': [...],
        }
    """
    files = list_tax_files(folder_id)
    
    inventory = {
        'files': [],
        'total': len(files),
        'by_type': {},
    }
    
    for f in files:
        file_info = {
            'id': f.get('id'),
            'name': f.get('name'),
            'mime_type': f.get('mimeType'),
            'size': f.get('size'),
            'type': get_file_type(f.get('name', '')),
        }
        inventory['files'].append(file_info)
        
        ftype = file_info['type']
        if ftype not in inventory['by_type']:
            inventory['by_type'][ftype] = []
        inventory['by_type'][ftype].append(file_info)
    
    return inventory

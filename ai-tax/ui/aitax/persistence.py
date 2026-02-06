"""
TaxForge - Data Persistence
Save and load tax data to/from local JSON file.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import base64
import hashlib

# Data directory
DATA_DIR = Path.home() / ".taxforge"
DATA_FILE = DATA_DIR / "tax_data.json"
BACKUP_DIR = DATA_DIR / "backups"

# Fields to persist (from TaxAppState)
PERSIST_FIELDS = [
    # Personal info
    "first_name", "last_name", "filing_status",
    # API key (will be obfuscated)
    "openai_api_key",
    # Documents
    "uploaded_files", "parsed_documents",
    # Tax data
    "w2_list", "form_1099_list", "form_1098_list", "form_5498_list",
    # Manual entries
    "rental_properties", "business_income", "other_income", "other_deductions",
    "dependents", "child_care_expenses",
    # Calculated values we want to persist
    "total_wages", "total_interest", "total_dividends", "total_capital_gains",
    "total_rental_income", "total_business_income", "total_other_income",
    "hsa_deduction", "self_employment_tax", "mortgage_interest_deduction",
    "adjusted_gross_income", "itemized_deductions", "standard_deduction",
    "total_deductions", "taxable_income", "total_tax", "total_withholding",
    "other_withholding", "refund_or_owed", "is_refund",
    "child_tax_credit", "other_dependent_credit", "child_care_credit", "total_credits",
    # Status
    "return_status", "return_generated",
]

# Fields that should be obfuscated (not encrypted, just not plain text)
SENSITIVE_FIELDS = ["openai_api_key"]


def _obfuscate(value: str) -> str:
    """Simple obfuscation for sensitive values (not real encryption)."""
    if not value:
        return ""
    return base64.b64encode(value.encode()).decode()


def _deobfuscate(value: str) -> str:
    """Reverse obfuscation."""
    if not value:
        return ""
    try:
        return base64.b64decode(value.encode()).decode()
    except:
        return value  # Return as-is if can't decode


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def save_state(state) -> bool:
    """
    Save state to JSON file.
    
    Args:
        state: TaxAppState instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        ensure_data_dir()
        
        # Extract fields to save
        data = {
            "_saved_at": datetime.now().isoformat(),
            "_version": "0.9.21",
        }
        
        for field in PERSIST_FIELDS:
            if hasattr(state, field):
                value = getattr(state, field)
                # Handle special types
                if isinstance(value, (list, dict)):
                    data[field] = value
                else:
                    data[field] = value
                    
                # Obfuscate sensitive fields
                if field in SENSITIVE_FIELDS and value:
                    data[field] = _obfuscate(str(value))
        
        # Create backup of existing file
        if DATA_FILE.exists():
            backup_name = f"tax_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = BACKUP_DIR / backup_name
            # Keep only last 5 backups
            existing_backups = sorted(BACKUP_DIR.glob("tax_data_*.json"))
            if len(existing_backups) >= 5:
                for old_backup in existing_backups[:-4]:
                    old_backup.unlink()
        
        # Write to file
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return True
        
    except Exception as e:
        print(f"[TaxForge] Error saving state: {e}")
        return False


def load_state(state) -> bool:
    """
    Load state from JSON file.
    
    Args:
        state: TaxAppState instance to populate
        
    Returns:
        True if data was loaded, False if no data or error
    """
    try:
        if not DATA_FILE.exists():
            print("[TaxForge] No saved data found, starting fresh")
            return False
        
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        print(f"[TaxForge] Loading saved data from {data.get('_saved_at', 'unknown')}")
        
        # Restore fields
        for field in PERSIST_FIELDS:
            if field in data:
                value = data[field]
                
                # Deobfuscate sensitive fields
                if field in SENSITIVE_FIELDS and value:
                    value = _deobfuscate(value)
                
                # Set the attribute
                if hasattr(state, field):
                    setattr(state, field, value)
        
        print(f"[TaxForge] Loaded: {len(data.get('w2_list', []))} W-2s, "
              f"{len(data.get('form_1099_list', []))} 1099s, "
              f"{len(data.get('rental_properties', []))} rentals")
        
        return True
        
    except Exception as e:
        print(f"[TaxForge] Error loading state: {e}")
        return False


def clear_saved_data() -> bool:
    """Clear all saved data."""
    try:
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        return True
    except Exception as e:
        print(f"[TaxForge] Error clearing data: {e}")
        return False


def get_data_info() -> Dict[str, Any]:
    """Get info about saved data."""
    info = {
        "exists": DATA_FILE.exists(),
        "path": str(DATA_FILE),
        "size": 0,
        "saved_at": None,
    }
    
    if DATA_FILE.exists():
        info["size"] = DATA_FILE.stat().st_size
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                info["saved_at"] = data.get("_saved_at")
                info["version"] = data.get("_version")
        except:
            pass
    
    return info

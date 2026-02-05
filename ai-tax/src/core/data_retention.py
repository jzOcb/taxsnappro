"""
Data Retention Policy — Automated enforcement.

Policy:
- Active tax returns: kept for duration of engagement + 30 days
- Filed returns: kept for 3 years (IRS audit window)  
- Uploaded documents (PDFs, images): deleted within 24 hours of processing
- Session data / temporary files: deleted immediately after processing
- User can request deletion at any time (right to be forgotten)

This module enforces these policies automatically.
"""

import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Retention periods
UPLOAD_RETENTION_HOURS = 24          # Raw uploads deleted after 24h
ACTIVE_RETURN_RETENTION_DAYS = 30    # Active returns kept 30 days after last access
FILED_RETURN_RETENTION_YEARS = 3     # Filed returns kept 3 years (IRS audit window)
TEMP_RETENTION_HOURS = 1             # Temp/session files deleted after 1h


class RetentionPolicy:
    """
    Enforce data retention policies on stored tax data.
    
    Usage:
        policy = RetentionPolicy(
            uploads_dir="data/uploads",
            returns_dir="data/returns",
            temp_dir="data/temp",
        )
        
        # Run cleanup (call daily via cron or on startup)
        deleted = policy.enforce()
        print(f"Cleaned up {deleted} expired files")
        
        # User requests deletion
        policy.delete_user_data(user_id="user123")
    """
    
    def __init__(self, uploads_dir: str, returns_dir: str, temp_dir: str = ""):
        self.uploads_dir = Path(uploads_dir)
        self.returns_dir = Path(returns_dir)
        self.temp_dir = Path(temp_dir) if temp_dir else None
        
        # Metadata file tracks retention info per return
        self.metadata_file = self.returns_dir / "_retention_metadata.json"
        self._metadata = self._load_metadata()
    
    def _load_metadata(self) -> dict:
        """Load retention metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_metadata(self):
        """Save retention metadata."""
        self.returns_dir.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, 'w') as f:
            json.dump(self._metadata, f, indent=2, default=str)
    
    def register_return(self, return_id: str, user_id: str, status: str = "active"):
        """Register a return with retention metadata."""
        self._metadata[return_id] = {
            "user_id": user_id,
            "status": status,  # active, filed, deleted
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat(),
            "filed_at": None,
            "expires_at": None,
        }
        self._update_expiry(return_id)
        self._save_metadata()
    
    def mark_filed(self, return_id: str):
        """Mark a return as filed — extends retention to 3 years."""
        if return_id in self._metadata:
            now = datetime.now(timezone.utc)
            self._metadata[return_id]["status"] = "filed"
            self._metadata[return_id]["filed_at"] = now.isoformat()
            self._metadata[return_id]["expires_at"] = (
                now + timedelta(days=FILED_RETURN_RETENTION_YEARS * 365)
            ).isoformat()
            self._save_metadata()
    
    def touch_return(self, return_id: str):
        """Update last accessed time (extends active retention)."""
        if return_id in self._metadata:
            self._metadata[return_id]["last_accessed"] = datetime.now(timezone.utc).isoformat()
            self._update_expiry(return_id)
            self._save_metadata()
    
    def _update_expiry(self, return_id: str):
        """Calculate expiry based on status."""
        meta = self._metadata.get(return_id)
        if not meta:
            return
        
        if meta["status"] == "filed":
            filed = datetime.fromisoformat(meta["filed_at"])
            meta["expires_at"] = (
                filed + timedelta(days=FILED_RETURN_RETENTION_YEARS * 365)
            ).isoformat()
        elif meta["status"] == "active":
            accessed = datetime.fromisoformat(meta["last_accessed"])
            meta["expires_at"] = (
                accessed + timedelta(days=ACTIVE_RETURN_RETENTION_DAYS)
            ).isoformat()
    
    def enforce(self) -> int:
        """
        Run retention enforcement — delete expired data.
        Returns number of items deleted.
        """
        deleted = 0
        now = datetime.now(timezone.utc)
        
        # 1. Clean up uploads older than 24 hours
        if self.uploads_dir.exists():
            for f in self.uploads_dir.iterdir():
                if f.is_file():
                    age_hours = (time.time() - f.stat().st_mtime) / 3600
                    if age_hours > UPLOAD_RETENTION_HOURS:
                        self._secure_delete(f)
                        deleted += 1
                        logger.info(f"Deleted expired upload: {f.name} (age: {age_hours:.1f}h)")
        
        # 2. Clean up temp files older than 1 hour
        if self.temp_dir and self.temp_dir.exists():
            for f in self.temp_dir.iterdir():
                if f.is_file():
                    age_hours = (time.time() - f.stat().st_mtime) / 3600
                    if age_hours > TEMP_RETENTION_HOURS:
                        self._secure_delete(f)
                        deleted += 1
        
        # 3. Clean up expired returns
        expired_returns = []
        for return_id, meta in self._metadata.items():
            if meta.get("status") == "deleted":
                continue
            
            expires_at = meta.get("expires_at")
            if expires_at:
                expiry = datetime.fromisoformat(expires_at)
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if now > expiry:
                    expired_returns.append(return_id)
        
        for return_id in expired_returns:
            self._delete_return_files(return_id)
            self._metadata[return_id]["status"] = "deleted"
            deleted += 1
            logger.info(f"Deleted expired return: {return_id}")
        
        if expired_returns:
            self._save_metadata()
        
        return deleted
    
    def delete_user_data(self, user_id: str) -> int:
        """
        Delete ALL data for a user (right to be forgotten).
        Returns number of items deleted.
        """
        deleted = 0
        
        for return_id, meta in list(self._metadata.items()):
            if meta.get("user_id") == user_id:
                self._delete_return_files(return_id)
                self._metadata[return_id]["status"] = "deleted"
                deleted += 1
        
        self._save_metadata()
        logger.info(f"Deleted all data for user {user_id}: {deleted} returns")
        return deleted
    
    def _delete_return_files(self, return_id: str):
        """Delete all files associated with a return."""
        # Delete encrypted return file
        enc_file = self.returns_dir / f"{return_id}.enc"
        if enc_file.exists():
            self._secure_delete(enc_file)
        
        # Delete any associated uploads
        if self.uploads_dir.exists():
            for f in self.uploads_dir.iterdir():
                if return_id in f.name:
                    self._secure_delete(f)
    
    @staticmethod
    def _secure_delete(path: Path):
        """Overwrite file with random data before deleting."""
        try:
            if path.is_file():
                size = path.stat().st_size
                with open(path, 'wb') as f:
                    f.write(os.urandom(size))
                path.unlink()
        except Exception as e:
            logger.error(f"Failed to securely delete {path}: {e}")
            # Try regular delete as fallback
            try:
                path.unlink()
            except Exception:
                pass
    
    def get_status(self) -> dict:
        """Get retention status summary."""
        active = sum(1 for m in self._metadata.values() if m["status"] == "active")
        filed = sum(1 for m in self._metadata.values() if m["status"] == "filed")
        deleted = sum(1 for m in self._metadata.values() if m["status"] == "deleted")
        
        upload_count = 0
        if self.uploads_dir.exists():
            upload_count = sum(1 for f in self.uploads_dir.iterdir() if f.is_file())
        
        return {
            "active_returns": active,
            "filed_returns": filed,
            "deleted_returns": deleted,
            "pending_uploads": upload_count,
        }

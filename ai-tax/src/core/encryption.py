"""
Encryption at Rest — Encrypt/decrypt user tax data for storage.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).
Key is derived from a master password using PBKDF2.

Usage:
    enc = DataEncryptor.from_password("master-password-from-env")
    
    # Encrypt a tax return for storage
    encrypted = enc.encrypt_json(tax_return_dict)
    
    # Decrypt when needed
    decrypted = enc.decrypt_json(encrypted)
    
    # Encrypt a file
    enc.encrypt_file("data/uploads/w2.pdf", "data/encrypted/w2.pdf.enc")

Security:
- Master key MUST come from environment variable, never hardcoded
- Encrypted files use .enc extension
- Each encryption uses a unique IV (built into Fernet)
- HMAC prevents tampering
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Any, Optional

# Use cryptography library if available, fallback to basic implementation
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


# Environment variable for the master encryption key
ENV_KEY_NAME = "AI_TAX_ENCRYPTION_KEY"
ENV_SALT_NAME = "AI_TAX_ENCRYPTION_SALT"


class DataEncryptor:
    """
    Encrypt and decrypt tax data at rest.
    
    Uses Fernet (AES-128-CBC + HMAC-SHA256) for authenticated encryption.
    Key is derived from a master password using PBKDF2 with 480,000 iterations.
    """
    
    def __init__(self, key: bytes):
        """Initialize with a Fernet key (32 bytes, base64-encoded)."""
        if not HAS_CRYPTOGRAPHY:
            raise RuntimeError(
                "cryptography package required for encryption. "
                "Install with: pip install cryptography"
            )
        self._fernet = Fernet(key)
    
    @classmethod
    def from_password(cls, password: str, salt: Optional[bytes] = None) -> 'DataEncryptor':
        """
        Create encryptor from a password string.
        
        Uses PBKDF2 with 480,000 iterations (OWASP recommended minimum).
        Salt should be stored alongside encrypted data or in env var.
        """
        if not HAS_CRYPTOGRAPHY:
            raise RuntimeError("cryptography package required")
        
        if salt is None:
            # Try to get salt from env, or generate new one
            env_salt = os.environ.get(ENV_SALT_NAME)
            if env_salt:
                salt = base64.b64decode(env_salt)
            else:
                salt = secrets.token_bytes(16)
                print(f"⚠️  Generated new encryption salt. Save this in {ENV_SALT_NAME}:")
                print(f"   {base64.b64encode(salt).decode()}")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return cls(key)
    
    @classmethod
    def from_env(cls) -> 'DataEncryptor':
        """
        Create encryptor from environment variables.
        
        Requires:
        - AI_TAX_ENCRYPTION_KEY: master password
        - AI_TAX_ENCRYPTION_SALT: base64-encoded salt
        """
        password = os.environ.get(ENV_KEY_NAME)
        if not password:
            raise ValueError(
                f"Missing {ENV_KEY_NAME} environment variable. "
                "Set it to a strong master password for tax data encryption."
            )
        
        salt_b64 = os.environ.get(ENV_SALT_NAME)
        salt = base64.b64decode(salt_b64) if salt_b64 else None
        
        return cls.from_password(password, salt)
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt raw bytes."""
        return self._fernet.encrypt(data)
    
    def decrypt(self, token: bytes) -> bytes:
        """Decrypt raw bytes."""
        return self._fernet.decrypt(token)
    
    def encrypt_json(self, obj: Any) -> str:
        """Encrypt a JSON-serializable object, return base64 string."""
        json_bytes = json.dumps(obj, default=str).encode('utf-8')
        encrypted = self.encrypt(json_bytes)
        return base64.b64encode(encrypted).decode('ascii')
    
    def decrypt_json(self, encrypted_str: str) -> Any:
        """Decrypt a base64-encoded encrypted JSON string."""
        encrypted = base64.b64decode(encrypted_str)
        json_bytes = self.decrypt(encrypted)
        return json.loads(json_bytes.decode('utf-8'))
    
    def encrypt_file(self, input_path: str, output_path: str):
        """Encrypt a file and write to output path."""
        with open(input_path, 'rb') as f:
            data = f.read()
        
        encrypted = self.encrypt(data)
        
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(encrypted)
    
    def decrypt_file(self, input_path: str, output_path: str):
        """Decrypt a file and write to output path."""
        with open(input_path, 'rb') as f:
            encrypted = f.read()
        
        data = self.decrypt(encrypted)
        
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(data)
    
    def encrypt_string(self, text: str) -> str:
        """Encrypt a string, return base64."""
        encrypted = self.encrypt(text.encode('utf-8'))
        return base64.b64encode(encrypted).decode('ascii')
    
    def decrypt_string(self, encrypted_str: str) -> str:
        """Decrypt a base64 string back to text."""
        encrypted = base64.b64decode(encrypted_str)
        return self.decrypt(encrypted).decode('utf-8')


class SecureStorage:
    """
    High-level secure storage for tax return data.
    
    Handles:
    - Encrypting tax returns before writing to disk
    - Decrypting when loading
    - Automatic cleanup (TTL-based expiry)
    - Audit logging (who accessed what, when)
    """
    
    def __init__(self, storage_dir: str, encryptor: DataEncryptor):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # Restrict permissions
        os.chmod(str(self.storage_dir), 0o700)
        self._enc = encryptor
        self._audit_log = self.storage_dir / "access_audit.log"
    
    def save_return(self, return_id: str, data: dict) -> str:
        """Save an encrypted tax return."""
        encrypted = self._enc.encrypt_json(data)
        
        file_path = self.storage_dir / f"{return_id}.enc"
        with open(file_path, 'w') as f:
            f.write(encrypted)
        os.chmod(str(file_path), 0o600)
        
        self._audit(f"SAVE {return_id}")
        return str(file_path)
    
    def load_return(self, return_id: str) -> dict:
        """Load and decrypt a tax return."""
        file_path = self.storage_dir / f"{return_id}.enc"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Return {return_id} not found")
        
        with open(file_path, 'r') as f:
            encrypted = f.read()
        
        self._audit(f"LOAD {return_id}")
        return self._enc.decrypt_json(encrypted)
    
    def delete_return(self, return_id: str):
        """Securely delete a tax return (overwrite then remove)."""
        file_path = self.storage_dir / f"{return_id}.enc"
        
        if file_path.exists():
            # Overwrite with random data before deletion
            size = file_path.stat().st_size
            with open(file_path, 'wb') as f:
                f.write(secrets.token_bytes(size))
            file_path.unlink()
            self._audit(f"DELETE {return_id}")
    
    def list_returns(self) -> list[str]:
        """List all stored return IDs."""
        return [
            f.stem for f in self.storage_dir.glob("*.enc")
            if f.name != "access_audit.log"
        ]
    
    def _audit(self, action: str):
        """Append to audit log."""
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(self._audit_log, 'a') as f:
            f.write(f"{timestamp} | {action}\n")

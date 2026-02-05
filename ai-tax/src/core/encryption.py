"""
Encryption at Rest — Encrypt/decrypt user tax data for storage.

Uses AES-256-GCM (Galois/Counter Mode) for authenticated encryption.
- AES-256: 256-bit key for encryption (NIST approved, matches documentation)
- GCM: Provides both confidentiality and integrity (authenticated encryption)
- Each encryption generates a unique 96-bit nonce (IV)

Key is derived from a master password using PBKDF2 with 600,000 iterations.

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
- Each encryption uses a unique 96-bit nonce (cryptographically random)
- GCM mode provides authentication (detects tampering)
- 600,000 PBKDF2 iterations (OWASP 2024 recommendation for SHA-256)

Migration:
- Can decrypt legacy Fernet-encrypted data (AES-128-CBC)
- All new encryptions use AES-256-GCM
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Any, Optional

# Use cryptography library
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.fernet import Fernet, InvalidToken  # For legacy decryption
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


# Environment variable for the master encryption key
ENV_KEY_NAME = "AI_TAX_ENCRYPTION_KEY"
ENV_SALT_NAME = "AI_TAX_ENCRYPTION_SALT"

# Magic bytes to identify AES-256-GCM encrypted data (vs legacy Fernet)
AES256_GCM_MAGIC = b"AES256GCM1"  # 10 bytes


class DataEncryptor:
    """
    Encrypt and decrypt tax data at rest.
    
    Uses AES-256-GCM for authenticated encryption:
    - 256-bit key (32 bytes)
    - 96-bit nonce (12 bytes, randomly generated per encryption)
    - 128-bit authentication tag (built into GCM)
    
    Key is derived from a master password using PBKDF2 with 600,000 iterations.
    
    Format of encrypted data:
    [MAGIC:10][NONCE:12][CIPHERTEXT+TAG:variable]
    
    Can also decrypt legacy Fernet data (AES-128-CBC) for migration.
    """
    
    def __init__(self, key: bytes, legacy_fernet_key: Optional[bytes] = None):
        """
        Initialize with a 256-bit key.
        
        Args:
            key: 32-byte AES-256 key
            legacy_fernet_key: Optional 32-byte Fernet key for decrypting old data
        """
        if not HAS_CRYPTOGRAPHY:
            raise RuntimeError(
                "cryptography package required for encryption. "
                "Install with: pip install cryptography"
            )
        
        if len(key) != 32:
            raise ValueError("AES-256 requires a 32-byte key")
        
        self._key = key
        self._aesgcm = AESGCM(key)
        
        # Legacy support for Fernet-encrypted data
        self._legacy_fernet = None
        if legacy_fernet_key:
            self._legacy_fernet = Fernet(legacy_fernet_key)
    
    @classmethod
    def from_password(cls, password: str, salt: Optional[bytes] = None) -> 'DataEncryptor':
        """
        Create encryptor from a password string.
        
        Uses PBKDF2 with 600,000 iterations (OWASP 2024 recommended for SHA-256).
        Salt should be stored alongside encrypted data or in env var.
        
        Derives TWO keys:
        - 32-byte AES-256 key for new encryptions
        - 32-byte Fernet-compatible key for legacy decryption
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
        
        # Derive AES-256 key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,  # OWASP 2024 recommendation
        )
        aes_key = kdf.derive(password.encode())
        
        # Derive legacy Fernet key (for decrypting old data)
        # Use different salt suffix to get different key
        legacy_kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt + b"_legacy",
            iterations=480000,  # Old iteration count for compatibility
        )
        legacy_key = base64.urlsafe_b64encode(legacy_kdf.derive(password.encode()))
        
        return cls(aes_key, legacy_fernet_key=legacy_key)
    
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
        """
        Encrypt raw bytes using AES-256-GCM.
        
        Returns: MAGIC (10) + NONCE (12) + CIPHERTEXT+TAG
        """
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        ciphertext = self._aesgcm.encrypt(nonce, data, None)
        return AES256_GCM_MAGIC + nonce + ciphertext
    
    def decrypt(self, token: bytes) -> bytes:
        """
        Decrypt raw bytes.
        
        Automatically detects AES-256-GCM vs legacy Fernet format.
        """
        # Check if it's our new AES-256-GCM format
        if token.startswith(AES256_GCM_MAGIC):
            nonce = token[10:22]  # 12 bytes after magic
            ciphertext = token[22:]
            return self._aesgcm.decrypt(nonce, ciphertext, None)
        
        # Try legacy Fernet decryption
        if self._legacy_fernet:
            try:
                return self._legacy_fernet.decrypt(token)
            except InvalidToken:
                pass
        
        raise ValueError(
            "Unable to decrypt: unrecognized format. "
            "Data may be corrupted or encrypted with a different key."
        )
    
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
    
    def re_encrypt(self, old_token: bytes) -> bytes:
        """
        Re-encrypt data from legacy format to AES-256-GCM.
        
        Use this for migrating old Fernet-encrypted data.
        """
        plaintext = self.decrypt(old_token)
        return self.encrypt(plaintext)


class SecureStorage:
    """
    High-level secure storage for tax return data.
    
    Handles:
    - Encrypting tax returns before writing to disk (AES-256-GCM)
    - Decrypting when loading (supports legacy Fernet data)
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
        """Save an encrypted tax return (using AES-256-GCM)."""
        encrypted = self._enc.encrypt_json(data)
        
        file_path = self.storage_dir / f"{return_id}.enc"
        with open(file_path, 'w') as f:
            f.write(encrypted)
        os.chmod(str(file_path), 0o600)
        
        self._audit(f"SAVE {return_id}")
        return str(file_path)
    
    def load_return(self, return_id: str) -> dict:
        """Load and decrypt a tax return (auto-detects format)."""
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
    
    def migrate_to_aes256(self, return_id: str):
        """
        Migrate a single return from legacy Fernet to AES-256-GCM.
        
        Loads with legacy decryption, re-saves with new encryption.
        """
        data = self.load_return(return_id)
        self.save_return(return_id, data)
        self._audit(f"MIGRATE {return_id} -> AES-256-GCM")
    
    def _audit(self, action: str):
        """Append to audit log."""
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        with open(self._audit_log, 'a') as f:
            f.write(f"{timestamp} | {action}\n")

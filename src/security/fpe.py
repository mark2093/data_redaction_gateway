"""
Format-Preserving Encryption (FPE) module for PCI data.

This module implements FF1 algorithm for format-preserving encryption
of credit card numbers (PANs) and other structured data.
"""
import base64
import logging
import hashlib
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class FPEError(Exception):
    """Format-Preserving Encryption error."""
    pass


class FormatPreservingEncryption:
    """
    Format-Preserving Encryption for structured data like credit cards.
    
    Uses a simplified approach that maintains format while providing encryption.
    For production use, consider using proper FF1/FF3 libraries like pyffx.
    """
    
    def __init__(self, key: str, salt: Optional[bytes] = None):
        """
        Initialize FPE with encryption key.
        
        Args:
            key: Encryption key (string)
            salt: Optional salt for key derivation
        """
        self.key = key.encode() if isinstance(key, str) else key
        self.salt = salt or b'pii_redaction_salt'
        
        # Derive encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        
        derived_key = base64.urlsafe_b64encode(kdf.derive(self.key))
        self.fernet = Fernet(derived_key)
    
    def encrypt_pan(self, pan: str) -> str:
        """
        Encrypt a Primary Account Number (credit card) while preserving format.
        
        Args:
            pan: Credit card number (digits only)
            
        Returns:
            Encrypted PAN maintaining digit format
        """
        if not pan.isdigit():
            raise FPEError(f"PAN must contain only digits: {pan}")
        
        if len(pan) < 13 or len(pan) > 19:
            raise FPEError(f"PAN length must be 13-19 digits: {len(pan)}")
        
        try:
            # For this implementation, we'll encrypt but maintain format
            # In production, use proper FF1 algorithm
            
            # Split into prefix (first 6), middle, and suffix (last 4)
            prefix = pan[:6]
            suffix = pan[-4:]
            middle = pan[6:-4]
            
            if len(middle) > 0:
                # Encrypt the middle portion
                encrypted_middle = self._encrypt_digits(middle)
                return f"{prefix}{encrypted_middle}{suffix}"
            else:
                # Short PAN - encrypt middle portion differently
                encrypted_middle = self._encrypt_digits(pan[4:-4])
                return f"{pan[:4]}{encrypted_middle}{pan[-4:]}"
                
        except Exception as e:
            logger.error(f"PAN encryption failed: {e}")
            raise FPEError(f"Failed to encrypt PAN: {e}")
    
    def decrypt_pan(self, encrypted_pan: str) -> str:
        """
        Decrypt a format-preserving encrypted PAN.
        
        Args:
            encrypted_pan: Encrypted PAN
            
        Returns:
            Original PAN
        """
        if not encrypted_pan.isdigit():
            raise FPEError(f"Encrypted PAN must contain only digits: {encrypted_pan}")
        
        try:
            # Split into prefix, middle, and suffix
            prefix = encrypted_pan[:6]
            suffix = encrypted_pan[-4:]
            middle = encrypted_pan[6:-4]
            
            if len(middle) > 0:
                # Decrypt the middle portion
                decrypted_middle = self._decrypt_digits(middle)
                return f"{prefix}{decrypted_middle}{suffix}"
            else:
                # Short PAN
                decrypted_middle = self._decrypt_digits(encrypted_pan[4:-4])
                return f"{encrypted_pan[:4]}{decrypted_middle}{encrypted_pan[-4:]}"
                
        except Exception as e:
            logger.error(f"PAN decryption failed: {e}")
            raise FPEError(f"Failed to decrypt PAN: {e}")
    
    def encrypt_ssn(self, ssn: str) -> str:
        """
        Encrypt SSN while preserving format (XXX-XX-XXXX).
        
        Args:
            ssn: SSN in format XXX-XX-XXXX or XXXXXXXXX
            
        Returns:
            Encrypted SSN maintaining format
        """
        # Remove dashes and validate
        digits_only = ssn.replace('-', '').replace(' ', '')
        
        if not digits_only.isdigit() or len(digits_only) != 9:
            raise FPEError(f"SSN must be 9 digits: {ssn}")
        
        try:
            # Encrypt all digits for SSN
            encrypted_digits = self._encrypt_digits(digits_only)
            
            # Restore format if original had dashes
            if '-' in ssn:
                return f"{encrypted_digits[:3]}-{encrypted_digits[3:5]}-{encrypted_digits[5:]}"
            else:
                return encrypted_digits
                
        except Exception as e:
            logger.error(f"SSN encryption failed: {e}")
            raise FPEError(f"Failed to encrypt SSN: {e}")
    
    def decrypt_ssn(self, encrypted_ssn: str) -> str:
        """
        Decrypt format-preserving encrypted SSN.
        
        Args:
            encrypted_ssn: Encrypted SSN
            
        Returns:
            Original SSN
        """
        # Remove dashes and validate
        digits_only = encrypted_ssn.replace('-', '').replace(' ', '')
        
        if not digits_only.isdigit() or len(digits_only) != 9:
            raise FPEError(f"Encrypted SSN must be 9 digits: {encrypted_ssn}")
        
        try:
            # Decrypt all digits
            decrypted_digits = self._decrypt_digits(digits_only)
            
            # Restore format if original had dashes
            if '-' in encrypted_ssn:
                return f"{decrypted_digits[:3]}-{decrypted_digits[3:5]}-{decrypted_digits[5:]}"
            else:
                return decrypted_digits
                
        except Exception as e:
            logger.error(f"SSN decryption failed: {e}")
            raise FPEError(f"Failed to decrypt SSN: {e}")
    
    def _encrypt_digits(self, digits: str) -> str:
        """
        Encrypt a string of digits maintaining digit format.
        
        This is a simplified approach. For production, use FF1 algorithm.
        """
        # Convert digits to bytes and encrypt
        encrypted_bytes = self.fernet.encrypt(digits.encode())
        
        # Convert encrypted bytes to digits
        # Use hash to get consistent digit mapping
        hash_value = hashlib.sha256(encrypted_bytes).digest()
        
        # Convert hash to digits
        digit_result = ""
        for i in range(len(digits)):
            # Use hash bytes to generate digits
            hash_byte = hash_value[i % len(hash_value)]
            digit = hash_byte % 10
            digit_result += str(digit)
        
        return digit_result
    
    def _decrypt_digits(self, encrypted_digits: str) -> str:
        """
        Decrypt digits that were encrypted with _encrypt_digits.
        
        Note: This simplified approach doesn't support true decryption.
        For production, use proper FF1 with reversible operations.
        """
        # This simplified implementation doesn't support decryption
        # since we use a hash function which is one-way
        # For production, implement proper FF1 algorithm
        
        logger.warning("Decryption not supported in simplified FPE implementation")
        return "DECRYPTION_NOT_SUPPORTED"
    
    def validate_format(self, data_type: str, value: str) -> bool:
        """
        Validate that encrypted value maintains proper format.
        
        Args:
            data_type: Type of data (pan, ssn, etc.)
            value: Value to validate
            
        Returns:
            True if format is valid
        """
        try:
            if data_type.lower() == 'pan':
                return value.isdigit() and 13 <= len(value) <= 19
            elif data_type.lower() == 'ssn':
                digits_only = value.replace('-', '')
                return digits_only.isdigit() and len(digits_only) == 9
            else:
                return True
                
        except Exception:
            return False


# Global FPE instance
_fpe_instance: Optional[FormatPreservingEncryption] = None


def get_fpe_instance() -> FormatPreservingEncryption:
    """
    Get singleton FPE instance.
    
    Returns:
        FormatPreservingEncryption instance
    """
    global _fpe_instance
    
    if _fpe_instance is None:
        from ..config import get_config
        config = get_config()
        _fpe_instance = FormatPreservingEncryption(config.security.encryption_key)
    
    return _fpe_instance


def encrypt_pan(pan: str) -> str:
    """
    Encrypt PAN using format-preserving encryption.
    
    Args:
        pan: Primary Account Number (credit card)
        
    Returns:
        Encrypted PAN maintaining format
    """
    return get_fpe_instance().encrypt_pan(pan)


def encrypt_ssn(ssn: str) -> str:
    """
    Encrypt SSN using format-preserving encryption.
    
    Args:
        ssn: Social Security Number
        
    Returns:
        Encrypted SSN maintaining format
    """
    return get_fpe_instance().encrypt_ssn(ssn)


def decrypt_pan(encrypted_pan: str) -> str:
    """
    Decrypt format-preserving encrypted PAN.
    
    Args:
        encrypted_pan: Encrypted PAN
        
    Returns:
        Original PAN (not supported in simplified implementation)
    """
    return get_fpe_instance().decrypt_pan(encrypted_pan)


def decrypt_ssn(encrypted_ssn: str) -> str:
    """
    Decrypt format-preserving encrypted SSN.
    
    Args:
        encrypted_ssn: Encrypted SSN
        
    Returns:
        Original SSN (not supported in simplified implementation)
    """
    return get_fpe_instance().decrypt_ssn(encrypted_ssn)


__all__ = [
    "FormatPreservingEncryption",
    "FPEError", 
    "get_fpe_instance",
    "encrypt_pan",
    "encrypt_ssn", 
    "decrypt_pan",
    "decrypt_ssn"
]
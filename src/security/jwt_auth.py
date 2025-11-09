"""
JWT Authentication and Token Management.

Provides JWT token generation, validation, and user session management.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ..core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # Test if bcrypt is working
    pwd_context.hash("test")
except Exception as e:
    logger.warning(f"Bcrypt initialization failed ({e}), falling back to SHA256")
    # Fallback to SHA256 for development/testing
    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    user_id: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    tenant_id: Optional[str] = None


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class User(BaseModel):
    """User model."""
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    tenant_id: Optional[str] = None
    disabled: bool = False
    hashed_password: Optional[str] = None


class JWTManager:
    """JWT token manager for authentication."""
    
    def __init__(
        self,
        secret_key: str = JWT_SECRET_KEY,
        algorithm: str = JWT_ALGORITHM,
        access_token_expire_minutes: int = JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days: int = JWT_REFRESH_TOKEN_EXPIRE_DAYS
    ):
        """
        Initialize JWT manager.
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm to use
            access_token_expire_minutes: Access token expiration time
            refresh_token_expire_days: Refresh token expiration time
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        
        # In-memory user store (replace with database in production)
        self._users: Dict[str, User] = {}
        self._revoked_tokens: set = set()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches
        """
        # Bcrypt has a 72-byte limit, truncate if necessary
        password_bytes = plain_password.encode('utf-8')[:72]
        return pwd_context.verify(password_bytes.decode('utf-8'), hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """
        Hash password.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        # Bcrypt has a 72-byte limit, truncate if necessary
        password_bytes = password.encode('utf-8')[:72]
        truncated_password = password_bytes.decode('utf-8')
        
        try:
            return pwd_context.hash(truncated_password)
        except Exception as e:
            # If bcrypt fails, try with even shorter password or use fallback
            logger.warning(f"Password hashing issue: {e}, using simplified approach")
            # Fallback: just use the first 50 characters
            return pwd_context.hash(password[:50])
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token.
        
        Args:
            data: Token payload data
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token data
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Check if token is revoked
            if token in self._revoked_tokens:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            roles: List[str] = payload.get("roles", [])
            permissions: List[str] = payload.get("permissions", [])
            tenant_id: str = payload.get("tenant_id")
            
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(
                username=username,
                user_id=user_id,
                roles=roles,
                permissions=permissions,
                tenant_id=tenant_id
            )
        
        except JWTError as e:
            logger.warning(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def revoke_token(self, token: str):
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
        """
        self._revoked_tokens.add(token)
        logger.info(f"Token revoked: {token[:20]}...")
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User object if authenticated, None otherwise
        """
        user = self._users.get(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        if user.disabled:
            return None
        return user
    
    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        roles: List[str] = None,
        permissions: List[str] = None,
        tenant_id: Optional[str] = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            username: Username
            password: Plain text password
            email: Email address
            full_name: Full name
            roles: User roles
            permissions: User permissions
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Created user
        """
        if username in self._users:
            raise ValueError(f"User {username} already exists")
        
        user = User(
            user_id=f"user_{len(self._users) + 1}",
            username=username,
            email=email,
            full_name=full_name,
            roles=roles or [],
            permissions=permissions or [],
            tenant_id=tenant_id,
            hashed_password=self.get_password_hash(password)
        )
        
        self._users[username] = user
        logger.info(f"User created: {username}")
        return user
    
    def get_user(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User or None
        """
        return self._users.get(username)
    
    def login(self, username: str, password: str) -> Token:
        """
        Login user and generate tokens.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Token response with access and refresh tokens
            
        Raises:
            HTTPException: If authentication fails
        """
        user = self.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create token payload
        token_data = {
            "sub": user.username,
            "user_id": user.user_id,
            "roles": user.roles,
            "permissions": user.permissions,
            "tenant_id": user.tenant_id
        }
        
        # Generate tokens
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"sub": user.username})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )


# Singleton instance
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """
    Get singleton JWT manager instance.
    
    Returns:
        JWTManager instance
    """
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> TokenData:
    """
    Get current user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Token data with user information
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    jwt_manager = get_jwt_manager()
    return jwt_manager.verify_token(credentials.credentials)


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Get current active user.
    
    Args:
        current_user: Current user token data
        
    Returns:
        User token data
    """
    return current_user


__all__ = [
    "JWTManager",
    "TokenData",
    "Token",
    "User",
    "get_jwt_manager",
    "get_current_user",
    "get_current_active_user",
]

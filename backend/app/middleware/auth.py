"""
Authentication middleware for ASA API.

Implements token-based authentication using API keys.
Supports both header and query parameter authentication.
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Callable
import secrets
import hashlib
from datetime import datetime, timedelta

from ..database import get_db
from ..models import APIKey


class APIKeyAuth:
    """
    API Key authentication handler.

    Supports multiple authentication methods:
    - Bearer token in Authorization header
    - API key in X-API-Key header
    - API key in query parameter
    """

    def __init__(self, require_auth: bool = True):
        """
        Initialize auth handler.

        Args:
            require_auth: Whether authentication is required
        """
        self.require_auth = require_auth
        self.bearer = HTTPBearer(auto_error=False)

    async def __call__(self, request: Request) -> Optional[APIKey]:
        """
        Authenticate request and return API key if valid.

        Args:
            request: FastAPI request object

        Returns:
            APIKey object if authenticated, None if auth not required

        Raises:
            HTTPException: If authentication fails
        """
        # Skip auth for public endpoints
        if not self.require_auth:
            return None

        # Try different auth methods
        api_key = await self._extract_api_key(request)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key. Provide via Authorization header, X-API-Key header, or api_key query param",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Validate API key
        db = next(get_db())
        try:
            key_record = self._validate_api_key(db, api_key)

            # Update last used timestamp
            key_record.last_used_at = datetime.utcnow()
            key_record.request_count += 1
            db.commit()

            return key_record

        except HTTPException:
            raise
        finally:
            db.close()

    async def _extract_api_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request using multiple methods.

        Priority:
        1. Authorization Bearer token
        2. X-API-Key header
        3. api_key query parameter

        Args:
            request: FastAPI request

        Returns:
            API key string or None
        """
        # Method 1: Authorization Bearer token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "").strip()

        # Method 2: X-API-Key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header:
            return api_key_header.strip()

        # Method 3: Query parameter
        api_key_param = request.query_params.get("api_key")
        if api_key_param:
            return api_key_param.strip()

        return None

    def _validate_api_key(self, db: Session, api_key: str) -> APIKey:
        """
        Validate API key against database.

        Args:
            db: Database session
            api_key: Raw API key string

        Returns:
            APIKey record if valid

        Raises:
            HTTPException: If key is invalid, revoked, or expired
        """
        # Hash the provided key
        key_hash = self._hash_api_key(api_key)

        # Look up in database
        key_record = db.query(APIKey).filter(
            APIKey.key_hash == key_hash
        ).first()

        if not key_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        # Check if revoked
        if key_record.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has been revoked"
            )

        # Check if expired
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired"
            )

        return key_record

    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """
        Hash API key for secure storage.

        Args:
            api_key: Raw API key

        Returns:
            SHA-256 hash of the key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure random API key.

        Returns:
            64-character hexadecimal API key
        """
        return secrets.token_hex(32)

    @staticmethod
    def create_api_key(
        db: Session,
        name: str,
        user_id: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000
    ) -> tuple[str, APIKey]:
        """
        Create a new API key.

        Args:
            db: Database session
            name: Human-readable name for the key
            user_id: Optional user identifier
            expires_in_days: Optional expiration in days
            rate_limit_per_minute: Requests per minute limit
            rate_limit_per_hour: Requests per hour limit

        Returns:
            Tuple of (raw_api_key, key_record)
            Note: raw_api_key is only returned once and cannot be retrieved later
        """
        # Generate key
        raw_key = APIKeyAuth.generate_api_key()
        key_hash = APIKeyAuth._hash_api_key(raw_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create record
        key_record = APIKey(
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            expires_at=expires_at,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_hour
        )

        db.add(key_record)
        db.commit()
        db.refresh(key_record)

        return raw_key, key_record


# Dependency for protected routes
def require_auth(request: Request) -> APIKey:
    """
    FastAPI dependency for protected routes.

    Usage:
        @app.get("/protected")
        def protected_route(api_key: APIKey = Depends(require_auth)):
            return {"user": api_key.user_id}
    """
    auth = APIKeyAuth(require_auth=True)
    import asyncio
    return asyncio.run(auth(request))


# Dependency for optional auth
def optional_auth(request: Request) -> Optional[APIKey]:
    """
    FastAPI dependency for optional authentication.

    Usage:
        @app.get("/optional")
        def optional_route(api_key: Optional[APIKey] = Depends(optional_auth)):
            if api_key:
                return {"authenticated": True, "user": api_key.user_id}
            return {"authenticated": False}
    """
    auth = APIKeyAuth(require_auth=False)
    import asyncio
    try:
        return asyncio.run(auth(request))
    except HTTPException:
        return None

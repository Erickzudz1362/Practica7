import os
from datetime import datetime, timedelta, timezone
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


JWT_SECRET = os.getenv("JWT_SECRET", "supermarket-dev-secret")
JWT_ALGORITHM = "HS256"
bearer = HTTPBearer()


def create_token(username: str, roles: Iterable[str], expires_minutes: int = 480) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "roles": list(roles),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expirado") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc


def require_roles(*allowed_roles: str):
    def dependency(user=Depends(current_user)):
        roles = set(user.get("roles", []))
        if allowed_roles and roles.isdisjoint(allowed_roles):
            raise HTTPException(status_code=403, detail="No autorizado para esta operación")
        return user

    return dependency

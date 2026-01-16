from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, status, HTTPException, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security.jwt_token import create_token
from app.auth.security.password import verify_password
from app.auth.security.refresh import generate_refresh_token, hash_refresh_token
from app.auth.schemas import AuthUser
from app.auth.dependencies import get_current_user_id
from app.core.database import get_db
from app.user.dao import UserDAO
from app.auth.dao import RefreshTokenDAO

router = APIRouter(prefix="/auth", tags=["auth"])

FAKE_PASSWORD = "$2b$12$q6VtHKLMERC2AkoXOFJ1eubTxllYp/dxUsR3coNAhhQYg.121Fqbi"

@router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id}

@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    authUser: AuthUser,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    user_dao = UserDAO(session)
    user = await user_dao.find_one_or_none(email=authUser.email.lower())

    is_valid = False
    if user:
        is_valid = verify_password(authUser.password, user.hashed_password)
    else:
        verify_password(authUser.password, FAKE_PASSWORD)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная почта или пароль",
        )

    access_ttl = timedelta(minutes=30)
    access_token = create_token(subject=str(user.id), ttl=access_ttl)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=int(access_ttl.total_seconds()),
        # secure=True,
    )

    refresh_plain = generate_refresh_token()
    refresh_hash = hash_refresh_token(refresh_plain)
    refresh_ttl_seconds = 60 * 60 * 24 * 30

    refresh_dao = RefreshTokenDAO(session)
    await refresh_dao.add(
        user_id=str(user.id),
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=refresh_ttl_seconds),
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_plain,
        httponly=True,
        samesite="lax",
        max_age=refresh_ttl_seconds,
        # secure=True,
    )

    return {
        "message": "Успешный вход",
        "user": {
            "id": user.id,
            "email": user.email,
        }
    }

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    dao = RefreshTokenDAO(session)
    refresh_plain = request.cookies.get("refresh_token")
    if refresh_plain:
        await dao.revoke(hash_refresh_token(refresh_plain))

    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "Успешный выход"}

@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    refresh_plain = request.cookies.get("refresh_token")
    if not refresh_plain:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизирован")

    refresh_hash = hash_refresh_token(refresh_plain)
    dao = RefreshTokenDAO(session)
    token = await dao.find_one_or_none(token_hash=refresh_hash)

    if (not token) or token.revoked_at or (token.expires_at <= datetime.now(timezone.utc)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизирован")

    await dao.revoke(refresh_hash)

    new_refresh_plain = generate_refresh_token()
    new_refresh_hash = hash_refresh_token(new_refresh_plain)
    refresh_ttl_seconds = 60 * 60 * 24 * 30

    await dao.add(
        user_id=token.user_id,
        token_hash=new_refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=refresh_ttl_seconds),
    )

    access_ttl = timedelta(minutes=30)
    access_token = create_token(subject=str(token.user_id), ttl=access_ttl)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=int(access_ttl.total_seconds()),
        # secure=True,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_plain,
        httponly=True,
        samesite="lax",
        max_age=refresh_ttl_seconds,
        # secure=True,
    )

    return {"message": "Токен обновлён"}
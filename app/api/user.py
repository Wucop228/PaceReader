from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.user.schemas import UserRegister
from app.user.dao import UserDAO
from app.auth.security.password import get_password_hash
from app.core.database import get_db

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserRegister,
    session: AsyncSession = Depends(get_db),
):
    dao = UserDAO(session)
    email = user_data.email.lower()
    user = await dao.find_one_or_none(email=email)

    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Пользователь с такой почтой уже существует"
        )

    user_dict = user_data.model_dump(exclude=['password'])
    user_dict["hashed_password"] = get_password_hash(user_data.password)

    try:
        new_user = await dao.add(**user_dict)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с такой почтой уже существует",
        )

    return {
        "message": f"Пользователь успешно зарегистрирован",
        "user_id": new_user.id,
    }
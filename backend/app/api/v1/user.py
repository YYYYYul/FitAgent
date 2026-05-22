from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import UserRegister, UserLogin, UserProfileUpdate, UserProfileResponse, TokenResponse
from app.services.user_service import (
    register_user,
    get_user_by_email,
    get_user_by_id,
    update_user_profile,
    verify_password,
    create_access_token,
)

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await register_user(db, req.email, req.password, req.display_name)
    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        user=UserProfileResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, req.email)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        user=UserProfileResponse.model_validate(user),
    )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserProfileResponse)
async def update_profile(user_id: str, req: UserProfileUpdate, db: AsyncSession = Depends(get_db)):
    update_data = req.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    user = await update_user_profile(db, user_id, **update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse.model_validate(user)

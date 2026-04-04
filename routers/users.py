# routers/users.py
# Defines all API endpoints related to users.
# This router is mounted at /api/users in main.py.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import PostResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,  # 201 Created is more semantically correct than 200 OK for resource creation.
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """POST /api/users — Creates a new user.

    Checks for uniqueness of both username and email before inserting.
    Returns 400 Bad Request if either value is already taken, rather than
    letting the database raise an IntegrityError (which would result in a
    less informative 500 Internal Server Error).
    """
    # Check if the username is already taken.
    result = await db.execute(
        select(models.User).where(models.User.username == user.username),
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check if the email is already registered.
    result = await db.execute(
        select(models.User).where(models.User.email == user.email),
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = models.User(
        username=user.username,
        email=user.email,
    )
    db.add(new_user)
    await db.commit()

    # Refresh to load database-generated values (id, defaults).
    await db.refresh(new_user)
    return new_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """GET /api/users/{user_id} — Returns a single user by their ID.

    Returns 404 if no user with the given ID exists.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """GET /api/users/{user_id}/posts — Returns all posts written by a specific user.

    First validates that the user exists to return a clear 404 instead of
    silently returning an empty list when the user ID is invalid.
    Posts are ordered from newest to oldest.
    """
    # Validate the user exists before querying their posts.
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc()),
    )
    posts = result.scalars().all()
    return posts


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,  # All fields are optional (PATCH semantics).
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """PATCH /api/users/{user_id} — Partially updates a user's profile.

    Only fields included in the request body are updated. Uniqueness checks
    are only performed when the new value differs from the current one,
    avoiding false conflicts when a user re-submits their existing username or email.
    Returns 404 if the user does not exist, 400 if the new username or email
    is already taken by another user.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Only check uniqueness if the username is actually changing.
    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(
            select(models.User).where(models.User.username == user_update.username),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # Only check uniqueness if the email is actually changing.
    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(
            select(models.User).where(models.User.email == user_update.email),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Apply only the fields that were explicitly provided in the request.
    # Unlike model_dump(exclude_unset=True), this manual approach gives finer
    # control and avoids iterating over fields that need individual handling.
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """DELETE /api/users/{user_id} — Deletes a user and all their posts.

    Returns 204 No Content on success (no response body).
    Returns 404 if the user does not exist.

    The cascade="all, delete-orphan" setting on User.posts in models.py
    ensures all posts owned by this user are automatically deleted as well.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()
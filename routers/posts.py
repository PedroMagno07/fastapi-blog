# routers/posts.py
# Defines all API endpoints related to blog posts.
# This router is mounted at /api/posts in main.py.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import PostCreate, PostResponse, PostUpdate

router = APIRouter()


@router.get("", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    """GET /api/posts — Returns all posts ordered from newest to oldest.

    Uses selectinload to eagerly fetch each post's author in one extra query,
    avoiding an N+1 query problem when serializing the nested author field.
    """
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc()),
    )
    posts = result.scalars().all()
    return posts


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,  # 201 Created is more semantically correct than 200 OK for resource creation.
)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """POST /api/posts — Creates a new blog post.

    Validates that the referenced user_id belongs to an existing user
    before inserting the post. Returns 404 if the user is not found.

    After committing, db.refresh loads the 'author' relationship so the
    response includes the full nested author object (required by PostResponse).
    """
    # Verify the author exists before creating the post.
    result = await db.execute(
        select(models.User).where(models.User.id == post.user_id),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    await db.commit()

    # Refresh the post and explicitly load the 'author' relationship.
    # This is necessary because expire_on_commit=False keeps the object alive
    # but relationships are not automatically populated after a commit.
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """GET /api/posts/{post_id} — Returns a single post by its ID.

    Returns 404 if no post with the given ID exists.
    """
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full(
    post_id: int,
    post_data: PostCreate,  # Full update requires all fields (PUT semantics).
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """PUT /api/posts/{post_id} — Fully replaces an existing post.

    All fields (title, content, user_id) must be provided in the request body.
    If user_id is being changed, validates that the new user exists.
    Returns 404 if the post or the new user is not found.
    """
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Only validate the new user_id if it's actually changing,
    # to avoid an unnecessary database query on unchanged ownership.
    if post_data.user_id != post.user_id:
        result = await db.execute(
            select(models.User).where(models.User.id == post_data.user_id),
        )
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    # Overwrite all fields unconditionally (full replacement).
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int,
    post_data: PostUpdate,  # Partial update — all fields are optional (PATCH semantics).
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """PATCH /api/posts/{post_id} — Partially updates an existing post.

    Only the fields included in the request body are updated; omitted fields
    keep their current values. Returns 404 if the post is not found.
    """
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # model_dump(exclude_unset=True) returns only the fields that were explicitly
    # sent in the request body, ignoring fields that were not provided.
    # This is the standard pattern for PATCH in Pydantic v2.
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """DELETE /api/posts/{post_id} — Deletes a post by its ID.

    Returns 204 No Content on success (no response body).
    Returns 404 if the post does not exist.
    """
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    await db.delete(post)
    await db.commit()
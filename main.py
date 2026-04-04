# main.py
# Entry point for the FastAPI application.
# Configures the app lifecycle, static file mounts, Jinja2 templates,
# API routers, page routes (SSR), and global exception handlers.

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import Base, engine, get_db
from routers import posts, users


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manages startup and shutdown events for the application.

    On startup: creates all database tables defined in the ORM models
    (if they don't already exist). This replaces the deprecated @app.on_event
    pattern introduced in older FastAPI versions.

    On shutdown: disposes the engine connection pool, releasing all
    database connections cleanly.
    """
    # --- Startup ---
    async with engine.begin() as conn:
        # run_sync is required because create_all is a synchronous SQLAlchemy call;
        # it's executed inside an async context by delegating to a thread.
        await conn.run_sync(Base.metadata.create_all)

    yield  # The application runs while execution is paused here.

    # --- Shutdown ---
    await engine.dispose()


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(lifespan=lifespan)

# Serve files from the /static directory under the /static URL prefix.
# Includes CSS, JavaScript, and default images.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve user-uploaded profile pictures from /media/profile_pics under /media.
app.mount("/media", StaticFiles(directory="media"), name="media")

# Jinja2Templates points FastAPI at the templates/ folder for server-side rendering.
templates = Jinja2Templates(directory="templates")

# Register the API routers.
# All user endpoints will be prefixed with /api/users.
# All post endpoints will be prefixed with /api/posts.
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


# ---------------------------------------------------------------------------
# Page routes (server-side rendered with Jinja2)
# ---------------------------------------------------------------------------

# Both "/" and "/posts" render the same home page.
# include_in_schema=False hides these HTML routes from the OpenAPI docs,
# keeping the docs focused on the JSON API endpoints.
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Renders the home page with all blog posts ordered newest first.

    Uses selectinload to eagerly load each post's author in a single
    extra query, avoiding N+1 queries when iterating over posts in the template.
    """
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc()),
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )


@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Renders the detail page for a single blog post.

    Returns a 404 error page if the post does not exist.
    Truncates the page title to the first 50 characters of the post title.
    """
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )
    post = result.scalars().first()

    if post:
        title = post.title[:50]  # Keep browser tab titles reasonably short.
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Renders a page listing all posts written by a specific user.

    Returns a 404 error page if the user does not exist.
    Posts are ordered newest first.
    """
    # First, verify the user exists before querying their posts.
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

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
):
    """Handles all HTTP exceptions across the application.

    Routes under /api/ receive the default JSON error response so that
    API clients (e.g. Postman, frontend JS) get machine-readable errors.

    All other routes (HTML pages) receive a rendered error.html template
    so the user sees a styled error page instead of raw JSON.
    """
    if request.url.path.startswith("/api"):
        # Delegate to FastAPI's built-in JSON error handler for API routes.
        return await http_exception_handler(request, exception)

    # Use the exception detail if available; otherwise fall back to a generic message.
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):
    """Handles Pydantic validation errors (HTTP 422 Unprocessable Entity).

    Like the HTTP exception handler above, API routes receive JSON and
    HTML page routes receive a rendered error template.

    This is raised automatically by FastAPI when request data fails
    Pydantic schema validation (e.g. missing required fields, wrong types).
    """
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
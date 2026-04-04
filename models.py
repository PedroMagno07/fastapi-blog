# models.py
# Defines the SQLAlchemy ORM models that map to database tables.
# Each class represents a table; each Mapped attribute represents a column.

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    """Represents a registered user of the blog.

    Maps to the 'users' table. Each user can own multiple posts;
    deleting a user automatically deletes all their posts (cascade).
    """

    __tablename__ = "users"

    # Primary key — auto-incremented integer, also indexed for fast lookups.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # unique=True prevents two users from sharing the same username or email.
    # nullable=False ensures these fields are always present.
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    # Optional profile picture filename stored in media/profile_pics/.
    # nullable=True / default=None means users start without a custom picture.
    image_file: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
    )

    # One-to-many relationship: one User → many Posts.
    # cascade="all, delete-orphan" means that when a User is deleted,
    # all associated Post records are automatically deleted too.
    # back_populates="author" links this side to Post.author.
    posts: Mapped[list[Post]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",
    )

    @property
    def image_path(self) -> str:
        """Returns the URL path to the user's profile picture.

        If the user has uploaded a custom picture, returns its media path.
        Otherwise falls back to the default static placeholder image.
        """
        if self.image_file:
            return f"/media/profile_pics/{self.image_file}"
        return "/static/profile_pics/default.jpg"


class Post(Base):
    """Represents a blog post written by a user.

    Maps to the 'posts' table. Each post belongs to exactly one User (author).
    """

    __tablename__ = "posts"

    # Primary key — auto-incremented integer, also indexed for fast lookups.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ForeignKey links each post to the user who created it.
    # index=True speeds up queries that filter posts by user (e.g. "all posts by user 5").
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Uses a lambda so datetime.now(UTC) is evaluated at post-creation time,
    # not when the module is first imported (which would freeze all posts
    # to the same timestamp).
    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Many-to-one relationship: many Posts → one User.
    # back_populates="posts" links this side to User.posts.
    author: Mapped[User] = relationship(back_populates="posts")
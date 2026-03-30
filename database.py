from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# sqlite+aiosqlite indicates SQLite with asynchronous driver
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

# check_same_thread=False allows multiple requests to access
# the database simultaneously (required for web applications)
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# expire_on_commit=False keeps objects accessible after commit,
# required to return data in the response without needing a new query
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass

# yield delivers the session to the request and only closes
# the database connection after the request is completed
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
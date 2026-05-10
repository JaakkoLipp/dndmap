from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


async def get_optional_db(request: Request) -> AsyncIterator[AsyncSession | None]:
    """Yields None when session_factory is not configured (in-memory / test mode)."""
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        yield None
        return
    async with factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
OptionalDbSession = Annotated[AsyncSession | None, Depends(get_optional_db)]

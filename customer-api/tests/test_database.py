from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


async def test_get_db_yields_session():
    """get_db should yield an AsyncSession and close it on cleanup."""
    gen = get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    # cleanup: close the generator which triggers the finally block
    await gen.aclose()

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database as _db

class BaseDAO:
    model = None

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_all(cls, **filter_by):
        async with _db.async_session_maker() as session:
            query = select(cls.model).filter_by(**filter_by)
            result = await session.execute(query)
            return result.scalars().all()

    async def find_one_or_none(cls, **filter_by):
        async with _db.async_session_maker() as session:
            query = select(cls.model).filter_by(**filter_by)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def find_one_or_none_by_filter(cls, *filter_conditions):
        async with _db.async_session_maker() as session:
            query = select(cls.model).filter(*filter_conditions)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def add(self, **data):
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj
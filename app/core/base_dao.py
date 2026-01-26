from sqlalchemy import update as sa_update, delete as sa_delete
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

class BaseDAO:
    model = None

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_all(self, **filter_by):
        query = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_one_or_none(self, **filter_by):
        query = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_one_or_none_by_filter(self, *filter_conditions):
        query = select(self.model).filter(*filter_conditions)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add(self, **data):
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, *, id: str, **data):
        """
        Обновляет объект по первичному ключу id.
        Возвращает обновлённый объект (или None, если не найден).
        """
        stmt = (
            sa_update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, *, id: str) -> bool:
        """
        Удаляет объект по id.
        Возвращает True если что-то удалилось.
        """
        stmt = sa_delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return (result.rowcount or 0) > 0
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.main_models import SuccessFulOperation
from sqlmodel import SQLModel

async def send_successful_operation(session: AsyncSession, operation: SuccessFulOperation):
    session.add(operation)
    await session.commit()
    await session.refresh(operation)
    return operation

async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
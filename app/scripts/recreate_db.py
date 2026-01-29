import os
import asyncio
import sys

app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, app_dir)
os.chdir(app_dir)
from core.database import wms_async_engine, Base

if os.path.exists('wms_dev.db'):
    os.remove('wms_dev.db')

async def go():
    async with wms_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == '__main__':
    asyncio.run(go())
    print('DB recreated async')

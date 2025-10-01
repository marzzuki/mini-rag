from sqlalchemy import select

from models.db_schemas import Asset
from models.enums import AssetTypeEnum

from .BaseDataModel import BaseDataModel


class AssetModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def create_asset(self, asset: Asset):
        if asset.asset_config is None:
            asset.asset_config = {}
        async with self.db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()
            await session.refresh(asset)
        return asset

    async def get_asset_record(self, asset_project_id: int, asset_name: str):
        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name,
                Asset.asset_type == AssetTypeEnum.FILE.value,
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
        return record

    async def get_all_project_assets(self, asset_project_id: int, asset_type: str):
        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_type == asset_type,
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
        return records

import math

from sqlalchemy import func
from sqlalchemy.future import select

from .BaseDataModel import BaseDataModel
from .db_schemas import Project


class ProjectModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def create_project(self, project: Project):
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            await session.commit()
            await session.refresh(project)

        return project

    async def get_project_or_create_one(self, project_id: int):
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.id == project_id)
                project = (await session.execute(query)).scalar_one_or_none()

                if project is None:
                    project = await self.create_project(
                        Project(
                        )
                    )

                return project

    async def get_all_project(self, page: int = 1, page_size: int = 10):
        async with self.db_client() as session:
            async with session.begin():
                total_documents = await session.execute(
                    select(
                        func.count(
                            Project.id,
                        ),
                    )
                ).scalar_one()

                total_pages = math.ceil(total_documents / page_size)

                query = select(Project).offset((page - 1) * page_size).limit(page_size)
                projects = (await session.execute(query)).scalar_one_or_none()
                return projects, total_pages

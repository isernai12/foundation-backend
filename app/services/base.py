from typing import Generic, TypeVar
from backend.app.repositories.base import BaseRepository

RepoType = TypeVar("RepoType", bound=BaseRepository)


class BaseService(Generic[RepoType]):
    """
    Base service class coordinating business logic and repository access.
    """
    def __init__(self, repository: RepoType):
        self.repository = repository

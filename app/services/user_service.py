from app.repositories.user_repo import UserRepository

class UserService:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def create_user(self, name: str):
        with self.uow_factory() as uow:
            repo = UserRepository(uow.session)
            user = repo.create(name)
            return user

    def get_users(self):
        with self.uow_factory() as uow:
            repo = UserRepository(uow.session)
            return repo.list()
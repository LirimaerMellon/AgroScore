from sqlalchemy import select
from app.models import User

class UserRepository:
    def __init__(self, session):
        self.session = session

    def create(self, name: str):
        user = User(name=name)
        self.session.add(user)
        return user

    def list(self):
        result = self.session.execute(select(User))
        return result.scalars().all()
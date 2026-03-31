from fastapi import APIRouter, Depends
from app.schemas.user_schema import UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter()

def get_user_service():
    from app.db import SessionLocal
    from app.uow import UnitOfWork

    return UserService(lambda: UnitOfWork(SessionLocal))


@router.post("/users", response_model=UserRead)
def create_user(data: UserCreate, service: UserService = Depends(get_user_service)):
    user = service.create_user(data.name)
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(service: UserService = Depends(get_user_service)):
    return service.get_users()
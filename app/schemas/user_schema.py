from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str

class UserRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
from pydantic import BaseModel

class User(BaseModel):
    id      : int
    group   : str

class Points(BaseModel):
    id          : int
    count       : int
    course      : str
    timestamp   : int
    description : str
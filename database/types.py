import datetime
from pydantic import BaseModel

class User(BaseModel):
    id      : int
    group   : str

class Points(BaseModel):
    id          : int
    count       : int
    course      : str
    description : str | None = None
    timestamp   : datetime.datetime | None = None
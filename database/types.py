from pydantic import BaseModel

class User(BaseModel):
    id      : int
    group   : str

class Points(BaseModel):
    id          : int
    count       : int
    course      : str
    description : str | None = None
    timestamp   : int | None = None

class Group(BaseModel):
    id      : int
    members : list[str]
    captain : int | None = None
    deputies: list[int] | None = None

    def __init__(self, **data):
        members = data.get("members")
        deputies = data.get("deputies")
        if isinstance(members, str):
            data["members"] = sorted([member for member in members.split("\n") if member])
        if isinstance(deputies, str):
            data["deputies"] = sorted([int(depaty) for depaty in deputies.split("\n") if depaty])
        super().__init__(**data)
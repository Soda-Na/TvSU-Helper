from aiogram.filters.callback_data  import CallbackData
from enum                           import Enum

class MenuAction(Enum):
    PROFILE = "profile"
    POINTS  = "points"
    CHANGE_GROUP = "change_group"

class MenuCallback(CallbackData, prefix="menu"):
    action: MenuAction
    user_id: int

class PointsAction(Enum):
    ADD = "add"
    DELETE = "delete"

class PointsCallback(CallbackData, prefix="points"):
    action: PointsAction
    user_id: int

class CourseAction(Enum):
    ADD = "add"
    INC = "inc"
    DELETE = "delete"
    DESC = "desc"
    
class CourseCallback(CallbackData, prefix="course"):
    action: CourseAction
    course: str
    count: int | None = None
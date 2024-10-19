from datetime                       import datetime

from aiogram.filters.callback_data  import CallbackData
from enum                           import Enum

class MenuAction(Enum):
    PROFILE = "p"
    POINTS  = "pts"
    MORE_DETAILS = "m"
    CHANGE_GROUP = "cg"

class MenuCallback(CallbackData, prefix="m"):
    action: MenuAction
    user_id: int

class PointsAction(Enum):
    ADD = "a"
    DELETE = "d"

class PointsCallback(CallbackData, prefix="p"):
    action: PointsAction
    user_id: int

class CourseAction(Enum):
    ADD_POINTS = "ap"
    ADD_COURSE = "ac"
    INC = "i"
    DELETE = "d"
    DELETE_CONFIRM = "dc"
    DESC = "dsc"
    MORE_DETAILS = "m"
    MORE_DETAILS_CONFIRM = "mc"
    
class CourseCallback(CallbackData, prefix="c", sep="|"):
    action: CourseAction
    course: str | None = None
    timestamp: datetime | None = None
    count: int | None = None
    description: str | None = None
    back_to: str | None = None
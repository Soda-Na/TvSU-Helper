from aiogram.fsm.state import State, StatesGroup

class PointsStates(StatesGroup):
    SetDescription = State()
    AddPoints = State()
    AddCourse = State()

class GroupStates(StatesGroup):
    SetMembers = State()
    SetCaptain = State()
    SetDeputy = State()
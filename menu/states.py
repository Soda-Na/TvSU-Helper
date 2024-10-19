from aiogram.fsm.state import State, StatesGroup

class MenuStates(StatesGroup):
    ChangeGroup = State()

class PointsStates(StatesGroup):
    SetDescription = State()
    AddPoints = State()
    AddCourse = State()
from aiogram                    import types, F, Router
from aiogram.filters.command    import CommandStart
from aiogram.utils              import keyboard
from aiogram.fsm.context        import FSMContext

from .callbacks                 import MenuCallback, MenuAction, PointsCallback, PointsAction, CourseCallback, CourseAction
from .states                    import MenuStates, PointsStates
from utils                      import back_button_markup, back_button

from database                   import UsersTable, PointsTable, User, Points

dispatcher = Router()

users_table = UsersTable()
points_table = PointsTable()

async def profile_menu(message: types.Message):
    user = await users_table.get_user(message.from_user.id)
    if user is None:
        await users_table.add_user(User(id=message.from_user.id, group="не указана"))
        user = await users_table.get_user(message.from_user.id)

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="📊 Мои баллы",
        callback_data=MenuCallback(
            action=MenuAction.POINTS,
            user_id=message.from_user.id
        )
    )
    buttons.button(
        text="👥 Сменить группу",
        callback_data=MenuCallback(
            action=MenuAction.CHANGE_GROUP,
            user_id=message.from_user.id
        )
    )
    buttons.adjust(1)
    
    await message.answer(
        f"👤 <b>Профиль:</b>\n"
        f"👥 <b>Группа:</b> {user.group}",
        reply_markup=buttons.as_markup()
    )

async def points_menu(message: types.Message): 
    user = await users_table.get_user(message.from_user.id)
    if user is None:
        await users_table.add_user(User(id=message.from_user.id, group="не указана"))
        user = await users_table.get_user(message.from_user.id)

    points = await points_table.get_sorted_points(message.from_user.id)

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="➕ Добавить баллы",
        callback_data=PointsCallback(
            action=PointsAction.ADD,
            user_id=message.from_user.id
        )
    )
    buttons.button(
        text="➖ Удалить баллы",
        callback_data=PointsCallback(
            action=PointsAction.DELETE,
            user_id=message.from_user.id
        )
    )
    buttons.adjust(1)

    text = "📊 <b>Мои баллы:</b>\n\n"
    for course, points in points.items():
        text += f"📚 <b>{course}:</b> {' '.join([str(i) for i in points])} | {sum(points)}\n"

    if text == "📊 <b>Мои баллы:</b>\n\n":
        text += "📚 <i>Нет данных</i>"

    await message.answer(
        text,
        reply_markup=buttons.as_markup()
    )    

@dispatcher.message(CommandStart())
async def start(message: types.Message):
    await profile_menu(message)

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.PROFILE))
async def profile(callback_query: types.CallbackQuery):
    await profile_menu(callback_query.message)

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.POINTS))
async def points(callback_query: types.CallbackQuery):
    await points_menu(callback_query.message)

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.CHANGE_GROUP))
async def change_group(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.ChangeGroup)
    await callback_query.message.answer(
        "Введите новую группу:"
    )

@dispatcher.message(MenuStates.ChangeGroup)
async def change_group(message: types.Message, state: FSMContext):
    await users_table.update_group(message.from_user.id, message.text)
    await state.clear()
    await message.answer(
        "Группа успешно изменена!",
        reply_markup=back_button_markup(MenuCallback(
            action=MenuAction.PROFILE,
            user_id=message.from_user.id
        ))
    )

@dispatcher.callback_query(PointsCallback.filter(F.action == PointsAction.ADD))
async def add_points(callback_query: types.CallbackQuery):
    points = await points_table.get_sorted_points(callback_query.from_user.id)

    buttons = keyboard.InlineKeyboardBuilder()
    for course in points.keys():
        buttons.button(
            text=course,
            callback_data=CourseCallback(
                action=CourseAction.ADD,
                course=course
            )
        )
    buttons.add(back_button(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.answer(
        "Выберите предмет:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(PointsCallback.filter(F.action == PointsAction.DELETE))
async def delete_points(callback_query: types.CallbackQuery):
    points = await points_table.get_sorted_points(callback_query.from_user.id)

    buttons = keyboard.InlineKeyboardBuilder()
    for course in points.keys():
        buttons.button(
            text=course,
            callback_data=CourseCallback(
                action=CourseAction.DELETE,
                course=course
            )
        )
    buttons.button(
        text="Добавить предмет",
        callback_data=CourseCallback(
            action=CourseAction.ADD
        )
    )
    buttons.add(back_button(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.answer(
        "Выберите предмет:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.ADD))
async def add_points_course(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    
    buttons = keyboard.InlineKeyboardBuilder()
    for i in range(1, 11):
        buttons.button(
            text=str(i),
            callback_data=CourseCallback(
                action=CourseAction.INC,
                course=callback_data.course,
                count=i
            )
        )
    buttons.add(back_button(PointsCallback(action=PointsAction.ADD, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(5)

    await callback_query.message.answer(
        "Выберите количество баллов:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DELETE))
async def delete_points_course(callback_data: CourseCallback, callback_query: types.CallbackQuery):
    points = await points_table.get_all_by_user(callback_query.from_user.id, callback_data.course)

    buttons = keyboard.InlineKeyboardBuilder()
    for point in points:
        buttons.button(
            text=f"{point.timestamp} | {point.count}",
            callback_data=CourseCallback(
                action=CourseAction.DELETE,
                course=callback_data.course,
                count=point.count
            )
        )
    buttons.add(back_button(PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.answer(
        "Выберите балл для удаления:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.INC))
async def add_points_count(callback_data: CourseCallback, callback_query: types.CallbackQuery):
    await points_table.add_points(
        Points(
            id=callback_data.user_id,
            count=callback_data.count,
            course=callback_data.course
        )
    )

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.buttons(
        text="Добавить описание",
        callback_data=CourseCallback(
            action=CourseAction.DESC,
            course=callback_data.course,
        )
    )
    buttons.add(back_button(PointsCallback(action=PointsAction.ADD, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.answer(
        "Балл успешно добавлен!",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DESC))
async def add_points_description(callback_data: CourseCallback, callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Введите описание:"
    )
    await state.set_state(PointsStates.SetDescription)

@dispatcher.message(PointsStates.SetDescription)
async def add_points_description(message: types.Message, state: FSMContext):
    await points_table.edit_description(
        message.from_user.id,
        message.text
    )
    await state.clear()
    await message.answer(
        "Описание успешно добавлено!",
        reply_markup=back_button_markup(PointsCallback(action=PointsAction.ADD, user_id=message.from_user.id).pack())
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DELETE))
async def delete_points_count(callback_data: CourseCallback, callback_query: types.CallbackQuery):
    await points_table.delete_points(
        callback_query.from_user.id,
        callback_data.course,
        callback_data.timestamp
    )
    await callback_query.answer("Балл успешно удален!")

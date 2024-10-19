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

async def profile_menu(message: types.Message, user_id: int = None):
    user = await users_table.get_user(user_id)
    if user is None:
        await users_table.add_user(User(id=user_id, group="не указана"))
        user = await users_table.get_user(user_id)

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="📊 Мои баллы",
        callback_data=MenuCallback(
            action=MenuAction.POINTS,
            user_id=user_id
        )
    )
    buttons.button(
        text="👥 Сменить группу",
        callback_data=MenuCallback(
            action=MenuAction.CHANGE_GROUP,
            user_id=user_id
        )
    )
    buttons.adjust(1)
    
    if message.from_user.id == message.bot.id:
        await message.edit_text(
            f"👤 <b>Профиль:</b>\n"
            f"👥 <b>Группа:</b> {user.group}",
            reply_markup=buttons.as_markup()
        )
        return

    await message.answer(
        f"👤 <b>Профиль</b>\n"
        f"👥 <b>Группа:</b> {user.group}",
        reply_markup=buttons.as_markup()
    )

async def points_menu(message: types.Message, user_id: int):
    user = await users_table.get_user(user_id)
    if user is None:
        await users_table.add_user(User(id=user_id, group="не указана"))
        user = await users_table.get_user(user_id)

    points = await points_table.get_sorted_points(user_id)

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="➕ Добавить баллы",
        callback_data=PointsCallback(
            action=PointsAction.ADD,
            user_id=user_id
        )
    )
    buttons.button(
        text="➖ Удалить баллы",
        callback_data=PointsCallback(
            action=PointsAction.DELETE,
            user_id=user_id
        )
    )
    buttons.button(
        text="🔍 Подробнее",
        callback_data=MenuCallback(
            action=MenuAction.MORE_DETAILS,
            user_id=user_id
        )
    )
    buttons.add(back_button(MenuCallback(action=MenuAction.PROFILE, user_id=user_id).pack()))
    buttons.adjust(1)

    text = "📊 <b>Мои баллы:</b>\n\n"
    for course, points in points.items():
        text += f"📚 <b>{course}:</b> {' '.join([str(i) for i in points])} | <b>{sum(points)}</b>\n"

    if text == "📊 <b>Мои баллы:</b>\n\n":
        text += "📚 <i>Нет данных</i>"

    if message.from_user.id == message.bot.id:
        await message.edit_text(
            text,
            reply_markup=buttons.as_markup()
        )
        return

    await message.answer(
        text,
        reply_markup=buttons.as_markup()
    )    

@dispatcher.message(CommandStart())
async def start(message: types.Message):
    await profile_menu(message, message.from_user.id)

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.PROFILE))
async def profile(callback_query: types.CallbackQuery):
    await profile_menu(callback_query.message, callback_query.from_user.id)

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.POINTS))
async def points(callback_query: types.CallbackQuery):
    await points_menu(callback_query.message, callback_query.from_user.id)

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.CHANGE_GROUP))
async def change_group(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.ChangeGroup)
    await callback_query.message.edit_text(
        "✏️ Введите новую группу:"
    )

@dispatcher.message(MenuStates.ChangeGroup)
async def change_group(message: types.Message, state: FSMContext):
    await users_table.update_group(message.from_user.id, message.text)
    await state.clear()
    await message.edit_text(
        "✅ Группа успешно изменена!",
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
                action=CourseAction.ADD_POINTS,
                course=course
            )
        )
    buttons.button(
        text="➕ Добавить предмет",
        callback_data=CourseCallback(
            action=CourseAction.ADD_COURSE
        )
    )
    buttons.add(back_button(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(
        "📚 Выберите предмет:",
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
    buttons.add(back_button(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(
        "📚 Выберите предмет:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.ADD_POINTS))
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

    await callback_query.message.edit_text(
        f"📊 Выберите количество баллов по предмету {callback_data.course}:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DELETE))
async def delete_points_course(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    points: list[Points] = await points_table.get_all_by_course(callback_query.from_user.id, callback_data.course)

    buttons = keyboard.InlineKeyboardBuilder()
    for point in points:
        buttons.button(
            text=f"{point.timestamp.strftime('%d.%m')} | {point.count}",
            callback_data=CourseCallback(
                action=CourseAction.DELETE_CONFIRM,
                course=callback_data.course,
                timestamp=point.timestamp,
                count=point.count,
                back_to=PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack()
            )
        )
    buttons.button(
        text="❌ Удалить все",
        callback_data=CourseCallback(
            action=CourseAction.DELETE_CONFIRM,
            course=callback_data.course+"allcourse",
            back_to=PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack()
        )
    )
    buttons.add(back_button(PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(
        "🗑️ Выберите балл для удаления:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.INC))
async def add_points_count(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    points = await points_table.add_points(
        Points(
            id=callback_query.from_user.id,
            count=callback_data.count,
            course=callback_data.course
        )
    )

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="✏️ Добавить описание",
        callback_data=CourseCallback(
            action=CourseAction.DESC,
            course=callback_data.course,
            timestamp=points.timestamp,
            back_to=PointsCallback(action=PointsAction.ADD, user_id=callback_query.from_user.id).pack()
        )
    )
    buttons.add(back_button(PointsCallback(action=PointsAction.ADD, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(
        "✅ Балл успешно добавлен!",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DESC))
async def add_points_description(callback_query: types.CallbackQuery, callback_data: CourseCallback, state: FSMContext):
    await callback_query.message.edit_text(
        "✏️ Введите описание:"
    )
    await state.set_state(PointsStates.SetDescription)
    await state.update_data(timestamp=callback_data.timestamp, course=callback_data.course, message=callback_query.message, back_to=callback_data.back_to)

@dispatcher.message(PointsStates.SetDescription)
async def add_points_description(message: types.Message, state: FSMContext):
    timestamp = (await state.get_data())["timestamp"]
    course = (await state.get_data())["course"]
    back_to = (await state.get_data())["back_to"]

    await message.delete()
    
    await points_table.edit_description(
        message.from_user.id,
        course,
        timestamp,
        message.text,
    )

    message = (await state.get_data())["message"]
    await state.clear()

    await message.edit_text(
        "✅ Описание успешно добавлено!",
        reply_markup=back_button_markup(back_to)
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DELETE_CONFIRM))
async def delete_points_count(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    if callback_data.course.endswith("allcourse"):
        callback_data.course = callback_data.course[:-9]
        await points_table.delete_all_points_by_course(
            callback_query.from_user.id,
            callback_data.course
        )
        await callback_query.message.edit_text(
            f"✅ Все баллы по предмету {callback_data.course} успешно удалены!",
            reply_markup=back_button_markup(callback_data.back_to)
        )
        return

    await points_table.delete_points(
        callback_query.from_user.id,
        callback_data.course,
        callback_data.timestamp
    )
    await callback_query.message.edit_text(
        "✅ Балл успешно удален!",
        reply_markup=back_button_markup(callback_data.back_to)
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.ADD_COURSE))
async def add_course(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(PointsStates.AddCourse)
    await state.update_data(message=callback_query.message)
    await callback_query.message.edit_text(
        "✏️ Введите название предмета:"
    )

@dispatcher.message(PointsStates.AddCourse)
async def add_course_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    course = message.text
    await message.delete()

    message = (await state.get_data())["message"]
    await state.clear()
    

    buttons = keyboard.InlineKeyboardBuilder()
    for i in range(1, 11):
        buttons.button(
            text=str(i),
            callback_data=CourseCallback(
                action=CourseAction.INC,
                course=course,
                count=i
            )
        )
    buttons.add(back_button(PointsCallback(action=PointsAction.ADD, user_id=user_id).pack()))
    buttons.adjust(5)

    await message.edit_text(
        f"📊 Выберите количество баллов по предмету {course}:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.MORE_DETAILS))
async def more_details_about_points(callback_query: types.CallbackQuery):
    points = await points_table.get_sorted_points(callback_query.from_user.id)

    buttons = keyboard.InlineKeyboardBuilder()
    for course in points.keys():
        buttons.button(
            text=course,
            callback_data=CourseCallback(
                action=CourseAction.MORE_DETAILS,
                course=course
            )
        )
    buttons.add(back_button(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(
        "📚 Выберите предмет:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.MORE_DETAILS))
async def more_details_about_course(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    points = await points_table.get_all_by_course(callback_query.from_user.id, callback_data.course)

    text = f"📚 <b>Выберите балл для просмотра:</b>\n\n"
    
    buttons = keyboard.InlineKeyboardBuilder()
    for point in points:
        buttons.button(
            text=f"{point.timestamp.strftime('%d.%m')} | {point.count}",
            callback_data=CourseCallback(
                action=CourseAction.MORE_DETAILS_CONFIRM,
                course=callback_data.course,
                timestamp=point.timestamp
            )
        )

    buttons.add(back_button(MenuCallback(action=MenuAction.MORE_DETAILS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(
        text,
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.MORE_DETAILS_CONFIRM))
async def more_details_about_course_confirm(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    points = await points_table.get_point(callback_query.from_user.id, callback_data.course, callback_data.timestamp)

    text = f"📚 <b>Подробности:</b>\n\n"
    text += f"📚 <b>Дата занесения:</b> {points.timestamp.strftime('%d.%m')}\n"
    text += f"📚 <b>Балл:</b> {points.count}\n"
    text += f"📚 <b>Описание:</b> {points.description if points.description is not None else 'не указано'}"

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="✏️ Изменить описание",
        callback_data=CourseCallback(
            action=CourseAction.DESC,
            course=callback_data.course,
            timestamp=callback_data.timestamp,
            back_to=MenuCallback(action=MenuAction.MORE_DETAILS, user_id=callback_query.from_user.id).pack()
        )
    )
    buttons.button(
        text="🗑️ Удалить балл",
        callback_data=CourseCallback(
            action=CourseAction.DELETE_CONFIRM,
            course=callback_data.course,
            timestamp=callback_data.timestamp,
            back_to=MenuCallback(action=MenuAction.MORE_DETAILS, user_id=callback_query.from_user.id).pack()
        )
    )
    buttons.add(back_button(CourseCallback(action=CourseAction.MORE_DETAILS, course=callback_data.course).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(
        text,
        reply_markup=buttons.as_markup()
    )
import datetime
import pytz

from aiogram                    import types, F, Router
from aiogram.filters.command    import CommandStart
from aiogram.utils              import keyboard
from aiogram.fsm.context        import FSMContext
from httpx                      import AsyncClient

from .callbacks                 import MenuCallback, MenuAction, PointsCallback, PointsAction, CourseCallback, CourseAction, GroupSelectCallback
from .states                    import PointsStates
from utils                      import back_button_markup, back_button, encode_rus_to_eng, decode_eng_to_rus, sort_key

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
        callback_data=MenuCallback(action=MenuAction.POINTS, user_id=user_id)
    )
    buttons.button(
        text="👥 Сменить группу",
        callback_data=MenuCallback(action=MenuAction.CHANGE_GROUP, user_id=user_id)
    )
    buttons.adjust(1)

    profile_text = f"👤 <b>Профиль</b>\n👥 <b>Группа:</b> {user.group}\n\n"
    if user.group != "не указана":
        profile_text += await schedule(user.group)
    else:
        profile_text += "📅 <i>Расписание недоступно, укажите группу.</i>"
    if message.from_user.id == message.bot.id:
        await message.edit_text(profile_text, reply_markup=buttons.as_markup())
    else:
        await message.answer(profile_text, reply_markup=buttons.as_markup())

async def schedule(group_name: str):
    async with AsyncClient() as client:
        response = await client.get("https://timetable.tversu.ru/api/v1/selectors")
        groups = response.json()["groups"]

        group_id = next((group["groupId"] for group in groups if group["groupName"] == group_name), None)
        if not group_id:
            return "Группа не найдена."

        response = await client.get(f"https://timetable.tversu.ru/api/v1/group?group={group_id}&type=classes")
        timetable = response.json()[0]

    start_date = datetime.datetime.strptime(timetable["start"], "%d.%m.%Y")
    timezone = pytz.timezone("Europe/Moscow")
    start_date = timezone.localize(start_date)
    current_date = datetime.datetime.now(tz=timezone)

    week_number = (current_date - start_date).days // 7
    week_type = "plus" if week_number % 2 == 1 else "minus"
    day_of_week = current_date.weekday() + 1

    def get_lessons(day, week):
        return sorted(
            [lesson for lesson in timetable["lessonsContainers"] if lesson["weekDay"] == day and (lesson["weekMark"] == "every" or lesson["weekMark"] == week)],
            key=lambda x: x["lessonNumber"]
        )

    lessons = get_lessons(day_of_week, week_type)
    if lessons and timetable["lessonTimeData"][lessons[-1]["lessonNumber"]]["end"] < current_date.strftime("%H:%M"):
        day_of_week += 1
        count = 0
        while True:
            if day_of_week == 8:
                day_of_week = 1
                week_type = "plus" if week_type == "minus" else "minus"
                count += 1
            lessons = get_lessons(day_of_week, week_type)
            if lessons:
                break
            day_of_week += 1

        text = f"📅 <b>Расписание на {'после' * count}завтра:</b>\n\n"
    else:
        text = "📅 <b>Расписание на сегодня:</b>\n\n"

    for lesson in lessons:
        lesson_time = timetable["lessonTimeData"][lesson["lessonNumber"]]
        if lesson_time["start"] < current_date.strftime("%H:%M") < lesson_time["end"] and 'завтра' not in text:
            text += f"🕒<b>{lesson_time['start']}-{lesson_time['end']}</b> <i>{lesson['texts'][1]}</i> | <code>{lesson['texts'][3].split()[-1]}</code>\n"
        else:
            text += f"🕒<code>{lesson_time['start']}-{lesson_time['end']}</code> <i>{lesson['texts'][1]}</i> | <code>{lesson['texts'][3].split()[-1]}</code>\n"

    return text

async def points_menu(message: types.Message, user_id: int):
    user = await users_table.get_user(user_id)
    if user is None:
        await users_table.add_user(User(id=user_id, group="не указана"))
        user = await users_table.get_user(user_id)

    points = await points_table.get_sorted_points(user_id)

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="➕ Добавить баллы",
        callback_data=PointsCallback(action=PointsAction.ADD, user_id=user_id)
    )
    buttons.button(
        text="➖ Удалить баллы",
        callback_data=PointsCallback(action=PointsAction.DELETE, user_id=user_id)
    )
    buttons.button(
        text="🔍 Подробнее",
        callback_data=MenuCallback(action=MenuAction.MORE_DETAILS, user_id=user_id)
    )
    buttons.add(back_button(MenuCallback(action=MenuAction.PROFILE, user_id=user_id).pack()))
    buttons.adjust(1)

    text = "📊 <b>Мои баллы:</b>\n\n"
    if points:
        for course, points in points.items():
            text += f"📚 <b>{course}:</b> {' '.join([str(i) for i in points])} | <b>{sum(points)}</b>\n"
    else:
        text += "📚 <i>Нет данных</i>"

    if message.from_user.id == message.bot.id:
        await message.edit_text(text, reply_markup=buttons.as_markup())
    else:
        await message.answer(text, reply_markup=buttons.as_markup())

async def handle_points_action(callback_query: types.CallbackQuery, action: CourseAction, text_if_empty: str):
    points = await points_table.get_sorted_points(callback_query.from_user.id)

    buttons = keyboard.InlineKeyboardBuilder()
    if points:
        text = "📚 <b>Выберите предмет:</b>"
        for course in points.keys():
            encoded_course = encode_rus_to_eng(course)
            buttons.button(
                text=course,
                callback_data=CourseCallback(action=action, course=encoded_course)
            )
    else:
        text = text_if_empty

    if action == CourseAction.ADD_POINTS:
        buttons.button(
            text="➕ Добавить предмет",
            callback_data=CourseCallback(action=CourseAction.ADD_COURSE)
        )
    
    buttons.add(back_button(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(text, reply_markup=buttons.as_markup())

@dispatcher.message(CommandStart())
async def start(message: types.Message):
    m = await message.answer("⏳ Загрузка...")
    await profile_menu(message, message.from_user.id)
    await m.delete()

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.PROFILE))
async def profile(callback_query: types.CallbackQuery):
    await profile_menu(callback_query.message, callback_query.from_user.id)

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.POINTS))
async def points(callback_query: types.CallbackQuery):
    await points_menu(callback_query.message, callback_query.from_user.id)

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.CHANGE_GROUP))
async def change_group(callback_query: types.CallbackQuery, state: FSMContext):
    async with AsyncClient() as client:
        response = await client.get("https://timetable.tversu.ru/api/v1/selectors")
        
        groups = response.json()["groups"]

        faculty_list = []
        for group in groups:
            faculty_name = group["facultyName"]
            faculty_list.append(faculty_name)

    buttons = keyboard.InlineKeyboardBuilder()
    for faculty in set(faculty_list):
        buttons.button(
            text=faculty,
            callback_data=GroupSelectCallback(faculty=faculty_list.index(faculty), user_id=callback_query.from_user.id)
        )
    buttons.add(back_button(MenuCallback(action=MenuAction.PROFILE, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text("👥 Выберите факультет:", reply_markup=buttons.as_markup())

@dispatcher.callback_query(GroupSelectCallback.filter(F.faculty != None))
async def select_group(callback_query: types.CallbackQuery, callback_data: GroupSelectCallback, state: FSMContext):
    async with AsyncClient() as client:
        response = await client.get("https://timetable.tversu.ru/api/v1/selectors")

        groups = response.json()["groups"]

        faculty_list = []
        faculty_dict = {}
        for group in groups:
            faculty_name = group["facultyName"]
            faculty_list.append(faculty_name)
            group_name = group["groupName"]
            if faculty_name not in faculty_dict:
                faculty_dict[faculty_name] = []
            faculty_dict[faculty_name].append(group_name)

        sorted_groups = sorted(faculty_dict[faculty_list[callback_data.faculty]], key=sort_key)

    buttons = keyboard.InlineKeyboardBuilder()
    for group in sorted_groups:
        buttons.button(
            text=group,
            callback_data=GroupSelectCallback(group=group, user_id=callback_query.from_user.id)
        )

    buttons.adjust(3)
    
    buttons.add(back_button(GroupSelectCallback(faculty=callback_data.faculty).pack()))

    await callback_query.message.edit_text("👥 Выберите группу:", reply_markup=buttons.as_markup())

@dispatcher.callback_query(GroupSelectCallback.filter(F.group != None))
async def set_group(callback_query: types.CallbackQuery, callback_data: GroupSelectCallback):
    await users_table.update_group(callback_query.from_user.id, callback_data.group)
    await callback_query.message.edit_text("👥 Группа успешно изменена!", reply_markup=back_button_markup(MenuCallback(action=MenuAction.PROFILE, user_id=callback_query.from_user.id).pack()))


@dispatcher.callback_query(PointsCallback.filter(F.action == PointsAction.ADD))
async def add_points(callback_query: types.CallbackQuery):
    await handle_points_action(callback_query, CourseAction.ADD_POINTS, "📚 <i>Вы еще не заносили ни одного балла.</i>")

@dispatcher.callback_query(PointsCallback.filter(F.action == PointsAction.DELETE))
async def delete_points(callback_query: types.CallbackQuery):
    await handle_points_action(callback_query, CourseAction.DELETE, "📚 <i>Вы еще не заносили ни одного балла.</i>")

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.ADD_POINTS))
async def add_points_course(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    decoded_course = decode_eng_to_rus(callback_data.course)
    
    buttons = keyboard.InlineKeyboardBuilder()
    for i in range(1, 11):
        buttons.button(
            text=str(i),
            callback_data=CourseCallback(action=CourseAction.INC, course=callback_data.course, count=i)
        )
    buttons.add(back_button(PointsCallback(action=PointsAction.ADD, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(5)

    await callback_query.message.edit_text(
        f"📊 Выберите количество баллов по предмету {decoded_course}:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DELETE))
async def delete_points_course(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    decoded_course = decode_eng_to_rus(callback_data.course)
    points: list[Points] = await points_table.get_all_by_course(callback_query.from_user.id, decoded_course)

    buttons = keyboard.InlineKeyboardBuilder()
    if points:
        for point in points:
            buttons.button(
                text=f"{datetime.datetime.fromtimestamp(point.timestamp).strftime('%d.%m')} | {point.count}",
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
                course=callback_data.course + "allcourse",
                back_to=PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack()
            )
        )
    else:
        await callback_query.message.edit_text(
            "📚 <i>Нет баллов для удаления по этому предмету.</i>",
            reply_markup=back_button_markup(PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack())
        )
        return

    buttons.add(back_button(PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(
        "🗑️ Выберите балл для удаления:",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.INC))
async def add_points_count(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    decoded_course = decode_eng_to_rus(callback_data.course)
    points = await points_table.add_points(
        Points(
            id=callback_query.from_user.id,
            count=callback_data.count,
            course=decoded_course,
            timestamp=int(datetime.datetime.now().timestamp())
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
    await callback_query.message.edit_text("✏️ Введите описание:")
    await state.set_state(PointsStates.SetDescription)
    await state.update_data(timestamp=callback_data.timestamp, course=callback_data.course, message=callback_query.message, back_to=callback_data.back_to)

@dispatcher.message(PointsStates.SetDescription)
async def add_points_description(message: types.Message, state: FSMContext):
    timestamp = (await state.get_data())["timestamp"]
    course = (await state.get_data())["course"]
    back_to: str = (await state.get_data())["back_to"]

    back_to = back_to.split(" ")
    prefix = back_to[0]
    action = back_to[1]

    for callbacks in [MenuCallback, PointsCallback, CourseCallback]:
        if prefix == callbacks.__prefix__:
            back_to = callbacks(action=action, user_id=message.from_user.id, course=course, timestamp=timestamp).pack()
            break

    await message.delete()
    
    await points_table.edit_description(
        message.from_user.id,
        decode_eng_to_rus(course),
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
        decoded_course = decode_eng_to_rus(callback_data.course[:-len("allcourse")])
        await points_table.delete_all_points_by_course(callback_query.from_user.id, decoded_course)
        await callback_query.message.edit_text(
            f"✅ Все баллы по предмету {decoded_course} успешно удалены!",
            reply_markup=back_button_markup(callback_data.back_to.replace("@", "|"))
        )
        return
    decoded_course = decode_eng_to_rus(callback_data.course)
    
    await points_table.delete_points(callback_query.from_user.id, decoded_course, callback_data.timestamp)
    await callback_query.message.edit_text(
        "✅ Балл успешно удален!",
        reply_markup=back_button_markup(callback_data.back_to.replace("@", "|"))
    )

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.ADD_COURSE))
async def add_course(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(PointsStates.AddCourse)
    await state.update_data(message=callback_query.message)
    await callback_query.message.edit_text("✏️ Введите название предмета:")

@dispatcher.message(PointsStates.AddCourse)
async def add_course_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    course = message.text
    await message.delete()

    message = (await state.get_data())["message"]
    await state.clear()
    
    encoded_course = encode_rus_to_eng(course)

    buttons = keyboard.InlineKeyboardBuilder()
    for i in range(1, 11):
        buttons.button(
            text=str(i),
            callback_data=CourseCallback(action=CourseAction.INC, course=encoded_course, count=i)
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
    if points:
        for course in points.keys():
            encoded_course = encode_rus_to_eng(course)
            buttons.button(
                text=course,
                callback_data=CourseCallback(action=CourseAction.MORE_DETAILS, course=encoded_course, user_id=callback_query.from_user.id)
            )
    else:
        await callback_query.message.edit_text(
            "📚 <i>Нет данных для отображения.</i>",
            reply_markup=back_button_markup(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack())
        )
        return

    buttons.add(back_button(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text("📚 Выберите предмет:", reply_markup=buttons.as_markup())

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.MORE_DETAILS))
async def more_details_about_course(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    decoded_course = decode_eng_to_rus(callback_data.course)
    points = await points_table.get_all_by_course(callback_query.from_user.id, decoded_course)

    text = f"📚 <b>Выберите балл для просмотра:</b>\n\n"
    
    buttons = keyboard.InlineKeyboardBuilder()
    if points:
        for point in points:
            print(point.timestamp)
            buttons.button(
                text=f"{datetime.datetime.fromtimestamp(point.timestamp).strftime('%d.%m')} | {point.count}",
                callback_data=CourseCallback(action=CourseAction.MORE_DETAILS_CONFIRM, course=callback_data.course, timestamp=point.timestamp, user_id=callback_query.from_user.id)
            )
            print(point.timestamp)
    else:
        await callback_query.message.edit_text(
            "📚 <i>Нет данных для отображения по этому предмету.</i>",
            reply_markup=back_button_markup(MenuCallback(action=MenuAction.MORE_DETAILS, user_id=callback_query.from_user.id).pack())
        )
        return

    buttons.add(back_button(MenuCallback(action=MenuAction.MORE_DETAILS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(text, reply_markup=buttons.as_markup())

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.MORE_DETAILS_CONFIRM))
async def more_details_about_course_confirm(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    decoded_course = decode_eng_to_rus(callback_data.course)
    print(decoded_course, callback_data.timestamp)
    points = await points_table.get_point(callback_query.from_user.id, decoded_course, callback_data.timestamp)
    print(points)

    text = f"📚 <b>Подробности:</b>\n\n"
    text += f"📚 <b>Дата занесения:</b> {datetime.datetime.fromtimestamp(points.timestamp).strftime('%d.%m')}\n"
    text += f"📚 <b>Балл:</b> {points.count}\n"
    text += f"📚 <b>Описание:</b> {points.description if points.description is not None else 'не указано'}"

    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="✏️ Изменить описание",
        callback_data=CourseCallback(
            user_id=callback_query.from_user.id,
            action=CourseAction.DESC,
            course=callback_data.course,
            timestamp=callback_data.timestamp,
            back_to=CourseCallback.__prefix__ + ' ' + CourseAction.MORE_DETAILS_CONFIRM.value
        )
    )
    buttons.button(
        text="🗑️ Удалить балл",
        callback_data=CourseCallback(
            user_id=callback_query.from_user.id,
            action=CourseAction.DELETE_CONFIRM,
            course=callback_data.course,
            timestamp=callback_data.timestamp,
            back_to=CourseCallback.__prefix__ + ' ' + CourseAction.MORE_DETAILS_CONFIRM.value
        )
    )
    buttons.add(back_button(CourseCallback(action=CourseAction.MORE_DETAILS, course=callback_data.course, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await callback_query.message.edit_text(text, reply_markup=buttons.as_markup())
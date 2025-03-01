import datetime
import pytz

from httpx import AsyncClient
from aiogram import types, F, Router
from aiogram.filters.command import CommandStart
from aiogram.utils import keyboard, formatting
from aiogram.fsm.context import FSMContext

from utils import (
    back_button_markup, back_button, 
    encode_rus_to_eng, decode_eng_to_rus, 
    sort_key, time_to_emoji
)
from database import (
    UsersTable, PointsTable, 
    GroupTable,
    User, Points
)
from .callbacks import (
    MenuCallback, MenuAction, 
    PointsCallback, PointsAction, 
    CourseCallback, CourseAction, 
    GroupSelectCallback, GroupMenuCallback, GroupMenuAction
)
from .states import PointsStates

dispatcher = Router()

users_table = UsersTable()
points_table = PointsTable()
group_table = GroupTable()

async def profile_menu(message: types.Message, user_id: int = None):
    user = await users_table.get_user(user_id) or await users_table.add_user(User(id=user_id, group="не указана"))
    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(text="📊 Мои баллы", callback_data=MenuCallback(action=MenuAction.POINTS, user_id=user_id))
    buttons.button(text="👥 Сменить группу", callback_data=MenuCallback(action=MenuAction.CHANGE_GROUP, user_id=user_id))
    if (await message.bot.get_chat_member(message.chat.id, message.from_user.id)).status == types.ChatMemberOwner:
        buttons.button(text="🔧 Настройки группы", callback_data=MenuCallback(action=MenuAction.GROUP_MENU, user_id=user_id))
    buttons.adjust(1)
    profile_text = f"👤 <b>Профиль</b>\n👥 <b>Группа:</b> {user.group}\n\n"
    profile_text += await schedule(user.group) if user.group != "не указана" else "📅 <i>Расписание недоступно, укажите группу.</i>"
    await (message.edit_text if message.from_user.id == message.bot.id else message.answer)(profile_text, reply_markup=buttons.as_markup())

def lessons_text_builder(lessons, timetable) -> str:
    max_length = max([len(lesson['texts'][1].replace(" (Лекция)", "").replace(" (Практика)", "").replace(" (Лаб. работа)", "")) for lesson in lessons])
    
    lessons_text = ""
    for lesson in lessons:
        lesson_type = "Л" if "Лекция" in lesson['texts'][1] else "П" if "Практика" in lesson['texts'][1] else "ЛР"
        lesson_time = timetable["lessonTimeData"][lesson["lessonNumber"]]
        lesson['texts'][1] = lesson['texts'][1].replace(" (Лекция)", "").replace(" (Практика)", "").replace(" (Лаб. работа)", "")

        emoji = time_to_emoji(lesson_time['start'])

        lessons_text += f"{emoji} {lesson_time['start']}-{lesson_time['end']} {lesson['texts'][1]:<{max_length}} {lesson_type:<2} | {lesson['texts'][3].split()[-1]}\n"

    return lessons_text 

def get_lessons(day, week, timetable):
    return sorted(
        [lesson for lesson in timetable["lessonsContainers"] if lesson["weekDay"] == day and (lesson["weekMark"] == "every" or lesson["weekMark"] == week)],
        key=lambda x: x["lessonNumber"]
    )

def choose_schedule_day(current_day, week_type, timetable, current_time, get_lessons):
    today_lessons = get_lessons(current_day, week_type, timetable)
    if today_lessons:
        last_lesson = today_lessons[-1]
        start_str = timetable["lessonTimeData"][last_lesson["lessonNumber"]]["start"]
        if datetime.datetime.strptime(start_str, "%H:%M").time() > current_time:
            return current_day, "на сегодня"
    offset = 1
    while True:
        total_day = current_day + offset
        weeks_passed = (total_day - 1) // 7
        check_day = (total_day - 1) % 7 + 1
        chk_week_type = week_type if weeks_passed % 2 == 0 else ("plus" if week_type == "minus" else "minus")
        if get_lessons(check_day, chk_week_type, timetable):
            label = "на завтра" if offset == 1 else "на " + "после" * (offset - 1) + "завтра"
            return check_day, label
        offset += 1

async def schedule(group_name: str):
    async with AsyncClient() as client:
        while True:
            try:
                response = await client.get("https://timetable.tversu.ru/api/v1/selectors", timeout=3)
            except:
                continue
            break
        groups = response.json()["groups"]
        group_id = next((group["groupId"] for group in groups if group["groupName"] == group_name), None)
        if not group_id:
            return "Группа не найдена."
        while True:
            try:
                response = await client.get(f"https://timetable.tversu.ru/api/v1/group?group={group_id}&type=classes", timeout=3)
            except:
                continue
            break
        timetable = response.json()[0]
    current_date = datetime.datetime.now(tz=pytz.timezone("Europe/Moscow"))
    current_day = current_date.weekday() + 1 

    start_date = pytz.timezone("Europe/Moscow").localize(datetime.datetime.strptime(timetable["start"], "%d.%m.%Y"))
    week_number = (current_date - start_date).days // 7
    week_type = "plus" if week_number % 2 == 1 else "minus"
    
    chosen_day, schedule_label = choose_schedule_day(
        current_day,
        week_type,
        timetable,
        current_date.time(),
        get_lessons
    )
    
    lessons = get_lessons(chosen_day, week_type, timetable)
    
    lessons_text = lessons_text_builder(lessons, timetable)
    lessons_text = formatting.Pre(lessons_text, language=f'📅 Расписание {schedule_label}:').as_html()
    lessons_text += (
        "\n"
        f"<code>📓 Обозначения: </code>\n"
        f"   <code>Л  - Лекция</code>\n"
        f"   <code>П  - Практика</code>\n"
        f"   <code>ЛР - Лабораторная работа</code>\n\n"
    )

    return lessons_text

async def points_menu(message: types.Message, user_id: int):
    user = await users_table.get_user(user_id) or await users_table.add_user(User(id=user_id, group="не указана"))
    points = await points_table.get_sorted_points(user_id)
    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(text="➕ Добавить баллы", callback_data=PointsCallback(action=PointsAction.ADD, user_id=user_id))
    buttons.button(text="➖ Удалить баллы", callback_data=PointsCallback(action=PointsAction.DELETE, user_id=user_id))
    buttons.button(text="🔍 Подробнее", callback_data=MenuCallback(action=MenuAction.MORE_DETAILS, user_id=user_id))
    buttons.add(back_button(MenuCallback(action=MenuAction.PROFILE, user_id=user_id).pack()))
    buttons.adjust(1)
    text = "📊 <b>Мои баллы:</b>\n\n" + "\n".join([f"📚 <b>{course}:</b> {' '.join(map(str, points))} | <b>{sum(points)}</b>" for course, points in points.items()]) if points else "📚 <i>Нет данных</i>"
    await (message.edit_text if message.from_user.id == message.bot.id else message.answer)(text, reply_markup=buttons.as_markup())

async def handle_points_action(callback_query: types.CallbackQuery, action: CourseAction, text_if_empty: str):
    points = await points_table.get_sorted_points(callback_query.from_user.id)
    buttons = keyboard.InlineKeyboardBuilder()
    text = "📚 <b>Выберите предмет:</b>" if points else text_if_empty
    for course in points.keys() if points else []:
        buttons.button(text=course, callback_data=CourseCallback(action=action, course=encode_rus_to_eng(course), user_id=callback_query.from_user.id))
    if action == CourseAction.ADD_POINTS:
        buttons.button(text="➕ Добавить предмет", callback_data=CourseCallback(action=CourseAction.ADD_COURSE, user_id=callback_query.from_user.id))
    buttons.add(back_button(MenuCallback(action=MenuAction.POINTS, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)
    await callback_query.message.edit_text(text, reply_markup=buttons.as_markup())

async def handle_course_action(callback_query: types.CallbackQuery, callback_data: CourseCallback, action: str, text: str, buttons: keyboard.InlineKeyboardBuilder):
    decoded_course = decode_eng_to_rus(callback_data.course)
    await callback_query.message.edit_text(text.format(decoded_course), reply_markup=buttons.as_markup())

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
        faculty_list = list(set(group["facultyName"] for group in groups))
    buttons = keyboard.InlineKeyboardBuilder()
    for faculty in faculty_list:
        buttons.button(text=faculty, callback_data=GroupSelectCallback(faculty=faculty_list.index(faculty), user_id=callback_query.from_user.id))
    buttons.add(back_button(MenuCallback(action=MenuAction.PROFILE, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    await state.update_data(faculty_list=faculty_list)

    await callback_query.message.edit_text("👥 Выберите факультет:", reply_markup=buttons.as_markup())

@dispatcher.callback_query(GroupSelectCallback.filter(F.faculty != None))
async def select_group(callback_query: types.CallbackQuery, callback_data: GroupSelectCallback, state: FSMContext):
    faculty_list = (await state.get_data())["faculty_list"]
    await state.clear()

    async with AsyncClient() as client:
        response = await client.get("https://timetable.tversu.ru/api/v1/selectors")
        groups = response.json()["groups"]
        faculty_dict = {}
        for group in groups:
            faculty_dict.setdefault(group["facultyName"], []).append(group["groupName"])
        sorted_groups = sorted(faculty_dict[faculty_list[callback_data.faculty]], key=sort_key)
    buttons = keyboard.InlineKeyboardBuilder()
    for group in sorted_groups:
        buttons.button(text=group, callback_data=GroupSelectCallback(group=group, user_id=callback_query.from_user.id))
    buttons.adjust(3)
    buttons.add(back_button(GroupSelectCallback(faculty=callback_data.faculty, user_id=callback_query.from_user.id).pack()))
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
    buttons = keyboard.InlineKeyboardBuilder()
    for i in range(1, 11):
        buttons.button(text=str(i), callback_data=CourseCallback(action=CourseAction.INC, course=callback_data.course, count=i, user_id=callback_query.from_user.id))
    buttons.add(back_button(PointsCallback(action=PointsAction.ADD, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(5)
    await handle_course_action(callback_query, callback_data, CourseAction.ADD_POINTS, "📊 Выберите количество баллов по предмету {}:", buttons)

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DELETE))
async def delete_points_course(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    decoded_course = decode_eng_to_rus(callback_data.course)
    points = await points_table.get_all_by_course(callback_query.from_user.id, decoded_course)
    buttons = keyboard.InlineKeyboardBuilder()
    if points:
        for point in points:
            buttons.button(text=f"{datetime.datetime.fromtimestamp(point.timestamp).strftime('%d.%m')} | {point.count}", callback_data=CourseCallback(action=CourseAction.DELETE_CONFIRM, course=callback_data.course, timestamp=point.timestamp, count=point.count, back_to=PointsCallback.__prefix__ + ' ' + PointsAction.DELETE.value, user_id=callback_query.from_user.id))
        buttons.button(text="❌ Удалить все", callback_data=CourseCallback(action=CourseAction.DELETE_CONFIRM, course=callback_data.course + "allcourse", back_to=PointsCallback.__prefix__ + ' ' + PointsAction.DELETE.value, user_id=callback_query.from_user.id))
    else:
        await callback_query.message.edit_text("📚 <i>Нет баллов для удаления по этому предмету.</i>", reply_markup=back_button_markup(PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack()))
        return
    buttons.add(back_button(PointsCallback(action=PointsAction.DELETE, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)
    await handle_course_action(callback_query, callback_data, CourseAction.DELETE, "🗑️ Выберите балл для удаления:", buttons)

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.INC))
async def add_points_count(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    decoded_course = decode_eng_to_rus(callback_data.course)
    points = await points_table.add_points(Points(id=callback_query.from_user.id, count=callback_data.count, course=decoded_course, timestamp=int(datetime.datetime.now().timestamp())))
    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(text="✏️ Добавить описание", callback_data=CourseCallback(user_id=callback_query.from_user.id, action=CourseAction.DESC, course=callback_data.course, timestamp=points.timestamp, back_to=PointsCallback.__prefix__ + ' ' + PointsAction.ADD.value))
    buttons.add(back_button(PointsCallback(action=PointsAction.ADD, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)
    await callback_query.message.edit_text("✅ Балл успешно добавлен!", reply_markup=buttons.as_markup())

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DESC))
async def add_points_description(callback_query: types.CallbackQuery, callback_data: CourseCallback, state: FSMContext):
    await callback_query.message.edit_text("✏️ Введите описание:")
    await state.set_state(PointsStates.SetDescription)
    await state.update_data(timestamp=callback_data.timestamp, course=callback_data.course, message=callback_query.message, back_to=callback_data.back_to)

@dispatcher.message(PointsStates.SetDescription)
async def add_points_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    timestamp, course, back_to = data["timestamp"], data["course"], data["back_to"].split(" ")
    prefix, action = back_to[0], back_to[1]
    for callbacks in [MenuCallback, PointsCallback, CourseCallback]:
        if prefix == callbacks.__prefix__:
            back_to = callbacks(action=action, user_id=message.from_user.id, course=course, timestamp=timestamp).pack()
            break
    await message.delete()
    await points_table.edit_description(message.from_user.id, decode_eng_to_rus(course), timestamp, message.text)
    await data["message"].edit_text("✅ Описание успешно добавлено!", reply_markup=back_button_markup(back_to))
    await state.clear()

@dispatcher.callback_query(CourseCallback.filter(F.action == CourseAction.DELETE_CONFIRM))
async def delete_points_count(callback_query: types.CallbackQuery, callback_data: CourseCallback):
    back_to = callback_data.back_to.split(" ")
    prefix, action = back_to[0], back_to[1]
    for callbacks in [MenuCallback, PointsCallback, CourseCallback]:
        if prefix == callbacks.__prefix__:
            back_to = callbacks(action=action, user_id=callback_query.from_user.id, course=callback_data.course, timestamp=callback_data.timestamp).pack()
            break
    if callback_data.course.endswith("allcourse"):
        decoded_course = decode_eng_to_rus(callback_data.course[:-len("allcourse")])
        await points_table.delete_all_points_by_course(callback_query.from_user.id, decoded_course)
        await callback_query.message.edit_text(f"✅ Все баллы по предмету {decoded_course} успешно удалены!", reply_markup=back_button_markup(back_to))
        return
    decoded_course = decode_eng_to_rus(callback_data.course)
    await points_table.delete_points(callback_query.from_user.id, decoded_course, callback_data.timestamp)
    await callback_query.message.edit_text("✅ Балл успешно удален!", reply_markup=back_button_markup(back_to))

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
            callback_data=CourseCallback(action=CourseAction.INC, course=encoded_course, count=i, user_id=user_id)
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
            (point.timestamp)
            buttons.button(
                text=f"{datetime.datetime.fromtimestamp(point.timestamp).strftime('%d.%m')} | {point.count}",
                callback_data=CourseCallback(action=CourseAction.MORE_DETAILS_CONFIRM, course=callback_data.course, timestamp=point.timestamp, user_id=callback_query.from_user.id)
            )
            (point.timestamp)
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
    (decoded_course, callback_data.timestamp)
    points = await points_table.get_point(callback_query.from_user.id, decoded_course, callback_data.timestamp)
    (points)

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

@dispatcher.callback_query(MenuCallback.filter(F.action == MenuAction.GROUP_MENU))
async def group_menu(callback_query: types.CallbackQuery):
    buttons = keyboard.InlineKeyboardBuilder()
    buttons.button(
        text="🔧 Изменить группу",
        callback_data=GroupMenuCallback(action=GroupMenuAction.CHANGE_GROUP, user_id=callback_query.from_user.id)
    )
    buttons.add(back_button(MenuCallback(action=MenuAction.PROFILE, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)

    group_data = await group_table.get_group(callback_query.message.chat.id)
    
    faculty = group_data.faculty if group_data else "не указан"
    group = group_data.group if group_data else "не указана"

    await callback_query.message.edit_text(
        f"👥 <b>Настройки группы:</b>\n\n"
        f"👥 <b>Факультет:</b> {faculty}\n"
        f"👥 <b>Группа:</b> {group}",
        reply_markup=buttons.as_markup()
    )

@dispatcher.callback_query(GroupMenuCallback.filter(F.action == GroupMenuAction.CHANGE_GROUP))
async def group_menu_change_group(callback_query: types.CallbackQuery, state: FSMContext):
    async with AsyncClient() as client:
        response = await client.get("https://timetable.tversu.ru/api/v1/selectors")
        groups = response.json()["groups"]
        faculty_list = list(set(group["facultyName"] for group in groups))
    buttons = keyboard.InlineKeyboardBuilder()
    for faculty in faculty_list:
        buttons.button(text=faculty, callback_data=GroupSelectCallback(faculty=faculty_list.index(faculty), user_id=callback_query.from_user.id))
    buttons.add(back_button(MenuCallback(action=MenuAction.GROUP_MENU, user_id=callback_query.from_user.id).pack()))
    buttons.adjust(1)
    await state.update_data(faculty_list=faculty_list)
    await callback_query.message.edit_text("👥 Выберите факультет:", reply_markup=buttons.as_markup())

@dispatcher.callback_query(GroupSelectCallback.filter(F.faculty != None))
async def group_menu_select_group(callback_query: types.CallbackQuery, callback_data: GroupSelectCallback, state: FSMContext):
    faculty_list = (await state.get_data())["faculty_list"]
    await state.clear()

    async with AsyncClient() as client:
        response = await client.get("https://timetable.tversu.ru/api/v1/selectors")
        groups = response.json()["groups"]
        faculty_dict = {}
        for group in groups:
            faculty_dict.setdefault(group["facultyName"], []).append(group["groupName"])
        sorted_groups = sorted(faculty_dict[faculty_list[callback_data.faculty]], key=sort_key)
    buttons = keyboard.InlineKeyboardBuilder()
    for group in sorted_groups:
        buttons.button(text=group, callback_data=GroupSelectCallback(group=group, user_id=callback_query.from_user.id))
    buttons.adjust(3)
    buttons.add(back_button(GroupSelectCallback(faculty=callback_data.faculty, user_id=callback_query.from_user.id).pack()))
    await state.update_data(faculty=faculty_list[callback_data.faculty])
    await callback_query.message.edit_text("👥 Выберите группу:", reply_markup=buttons.as_markup())

@dispatcher.callback_query(GroupSelectCallback.filter(F.group != None))
async def group_menu_set_group(callback_query: types.CallbackQuery, callback_data: GroupSelectCallback, state: FSMContext):
    faculty = (await state.get_data())["faculty"]
    await state.clear()
    await group_table.update_group(callback_query.message.chat.id, faculty, callback_data.group)
    await callback_query.message.edit_text("👥 Группа успешно изменена!", reply_markup=back_button_markup(GroupMenuCallback(action=GroupMenuAction.CHANGE_GROUP, user_id=callback_query.from_user.id).pack()))
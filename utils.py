from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types          import InlineKeyboardMarkup, InlineKeyboardButton

def back_button_markup(callback_data: str) -> InlineKeyboardMarkup:
    buttons = InlineKeyboardBuilder()
    buttons.button(
        text="🔙 Назад",
        callback_data=callback_data
    )
    buttons.adjust(1)
    return buttons.as_markup()

def back_button(callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="🔙 Назад",
        callback_data=callback_data
    )

translit_dict = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'jo', 
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'jj', 'к': 'k', 'л': 'l', 'м': 'm', 
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 
    'ф': 'f', 'х': 'kh', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'shh', 'ъ': 'q', 
    'ы': 'y', 'ь': 'x', 'э': 'je', 'ю': 'yu', 'я': 'ya',
    
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Jo', 
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Jj', 'К': 'K', 'Л': 'L', 'М': 'M', 
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 
    'Ф': 'F', 'Х': 'Kh', 'Ц': 'C', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shh', 
    'Ъ': 'Q', 'Ы': 'Y', 'Ь': 'X', 'Э': 'Je', 'Ю': 'Yu', 'Я': 'Ya'
}

reverse_translit_dict = {v: k for k, v in translit_dict.items()}

def encode_rus_to_eng(text):
    result = []
    for char in text:
        result.append(translit_dict.get(char, char))
    return ''.join(result)

def decode_eng_to_rus(text):
    result = []
    i = 0
    while i < len(text):
        for length in (3, 2, 1):  
            chunk = text[i:i + length]
            if chunk in reverse_translit_dict:
                result.append(reverse_translit_dict[chunk])
                i += length
                break
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)

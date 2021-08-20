import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton

from main import *

curr_state = str()  # Текущее состояние(установка прокси или апи и т.п.)

TOKEN = '1931690072:AAEI4Qf2ZVIqDQ1CP8xQs5i22Irzis30RnU'  # Токен бота

with open('faq.txt', encoding='UTF-8') as fl:   # Достаем текст faq из файла
    faq = ''.join(fl.readlines())

faq_btn = ReplyKeyboardMarkup(keyboard=[            # Создаем кнопку для faq
    [KeyboardButton(text='FAQ')],
], resize_keyboard=True, one_time_keyboard=False)


# Функция определения действия (платеж, прокси или апи)
def get_current_state(text):
    try:
        if text[:7].lower() == 'preauth' or text[:6].lower() == 'charge':
            return 'pay'
    except Exception as e:
        print(e)

    try:
        if ('sk_test' in text or 'sk_live' in text or 'rk_test' in text or 'rk_live' in text) and len(text) == 107:
            return 'key'
    except Exception as e:
        print(e)

    try:
        if text[:4] == 'http' or text[:6] == 'socks5':
            return 'proxy'
    except Exception as e:
        print(e)

    try:
        if text.lower() == 'proxy -s' or text.lower() == 'proxy off' or text.lower() == 'proxy stop':
            return 'del proxy'
    except Exception as e:
        print(e)


# Функция обработки событий с ботом
def handler(data):
    global curr_state

    uid = data['from']['id']  # Получаем ID пользователя

    curr_state = get_current_state(data['text'])    # Устанавливаем текущее состояние

    if data['text'] == '/start':
        bot.sendMessage(uid, faq, reply_markup=faq_btn)     # Выводим faq

    if data['text'].lower() == 'faq':                       # Выводим faq
        bot.sendMessage(uid, faq)

    if curr_state == 'pay':
        rec = valid_payment(data['text'])  # Получаем проверенные данные

        if rec:  # Если данные прошли проверку, то пробуем провести оплату
            if rec == 'proxy error':
                bot.sendMessage(uid, 'Invalid proxy. Update/delete proxy.')
            else:
                charge = get_payment(rec)  # Получаем статус платежа
                try:
                    bot.sendMessage(uid, str(charge))  # Выводим пользователю
                except Exception as e:
                    print(e)
                    bot.sendMessage(uid, str(charge))
        else:
            bot.sendMessage(uid, 'Incorrect data. Try again.')

    elif curr_state == 'proxy':             # Установка прокси
        bot.getMe()
        if not set_new_proxy(data['text']):
            bot.sendMessage(uid, 'Invalid proxy.')
        else:
            bot.sendMessage(uid, 'New proxy was set.')
            curr_state = str()

    elif curr_state == 'key':  # Прием нового ключа
        set_stripe_key(data['text'])
        curr_state = str()
        bot.sendMessage(uid, 'Api-key was changed successfully.')

    elif curr_state == 'del proxy':     # Удаление прокси
        clear_proxy()
        bot.sendMessage(uid, 'Proxy was clear.')


bot = telepot.Bot(TOKEN)
print(bot.getMe())
MessageLoop(bot, handler).run_as_thread()

while True:
    time.sleep(1)

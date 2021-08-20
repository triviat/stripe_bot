import time
import stripe
from stripe import error

from valid_proxy import is_bad_proxy

with open('token.txt') as f:
    stripe.api_key = f.readline()

# SOCKS4 - 1 | SOCKS5 - 2 | HTTP - 3
with open('proxy.txt') as flp:
    def_proxy = flp.readline()
    if def_proxy == '':
        def_proxy = [None, None, None]

# card number, charge
buffer = [None, None]


def get_stripe_key():
    with open('token.txt') as fl:
        stripe.api_key = fl.readline()

    return stripe.api_key


# Функция установки нового ключа
def set_stripe_key(key):
    with open('token.txt', 'w') as fl:
        fl.write(key)
    stripe.api_key = get_stripe_key()


# Функция валидации данных
def valid_payment(payment_str):
    with open('proxy.txt') as pr:
        proxy = pr.readline()
    if not set_new_proxy(proxy) and proxy != '':
        return 'proxy error'

    args = payment_str.split('|')  # Разбиваем строку на отдельные элементы
    kind = args[0]
    args = args[1:]
    if len(args) < 16 or len(args) > 17:  # Проверяем кол-во элементов, их должно быть либо 16, либо 17
        return []  # Возвращаем пустой список

    for i in range(len(args)):  # Заменяем элементы с прочерком на None
        if args[i] == '-':
            args[i] = None

    if len(args) == 17 and args[-1] is not None:
        set_stripe_key(args[-1])

    stripe.api_key = get_stripe_key()

    args.insert(0, kind)
    return args  # Возвращаем реквизиты


def set_new_proxy(pr):
    try:
        global def_proxy
        new_proxy = pr.split('|')
        protocol = str()
        if new_proxy[0].lower() == 'http':
            protocol = 'http'
            new_proxy = [3, new_proxy[1].split(':')[0], int(new_proxy[1].split(':')[1])]
        elif new_proxy[0].lower() == 'socks5':
            protocol = 'socks5'
            new_proxy = [2, new_proxy[1].split(':')[0], int(new_proxy[1].split(':')[1])]

        if not is_bad_proxy(new_proxy):
            def_proxy = new_proxy
            with open('proxy.txt', 'w') as fs:
                fs.write(protocol + '|' + str(def_proxy[1]) + ':' + str(def_proxy[2]))
            return 1
        return 0
    except Exception as e:
        print(e)
        return 0


def clear_proxy():
    global def_proxy
    def_proxy = [None, None, None]
    with open('proxy.txt', 'w') as fd:
        fd.write('')


def check_zip_n_street(charge):
    resp = ''
    if charge.source.address_line1_check == 'fail':
        resp = '\n\nStreet check: Failed'
    if charge.source.address_zip_check == 'fail':
        if resp:
            resp += '\nZip check: Failed'
        else:
            resp = '\n\nZip check: Failed'
    return resp


def get_card_name(num):
    if type(num) is type(str()):
        if num[0] == '3':
            return 'AMEX **** ' + num[12:]
        if num[0] == '4':
            return 'Visa **** ' + num[12:]
        if num[0] == '5':
            return 'MasterCard **** ' + num[12:]
        if num[0] == '6':
            return 'Discover **** ' + num[12:]
    else:
        print(num)
        return None


def get_error_message(buf, e):
    try:
        return get_card_name(buf[0]) + '\n\nThe bank returned the decline code: ' + e.error.decline_code
    except Exception as exc:
        print(exc)
        try:
            return get_card_name(buf[0]) + '\n\nWrong request. ' + str(e.user_message)
        except Exception as exc_2:
            print(exc_2)
            return get_card_name(buf[0]) + '\n\n' + str(e.user_message)


# Функция для проведения перевода
def get_payment(args):
    # amount 0, name 1, card_num 2, card_month 3, card_year 4, card_cvc 5, email 6, phone 7,
    # description 8, statement description 9, country 10, city 11, state 12,
    # address_line1 13, address_line2 14, zip 15 (всего - 16)

    import httplib2
    import socks

    global def_proxy, buffer

    socks.set_default_proxy(def_proxy[0], def_proxy[1], def_proxy[2])
    socks.wrapmodule(httplib2)

    # now all calls through httplib2 should use the proxy settings
    proxy_client = httplib2.Http()

    kind = args[0]
    args = args[1:]
    buffer[0] = args[2]

    try:
        token = stripe.Token.create(
            card={
                "number": args[2],
                "exp_month": args[3],
                "exp_year": args[4],
                "cvc": args[5],
                "name": args[1],
                "address_city": args[11],
                "address_country": args[10],
                "address_state": args[12],
                "address_line1": args[13],
                "address_line2": args[14],
                "address_zip": args[15]
            }
        )

        time.sleep(2)
        if kind == 'preauth':
            customer = stripe.Customer.create(  # Создаем нового пользователся с данной картой
                card=token,
                email=args[6],
                phone=args[7],
                description=args[8],
                name=args[1],
                address={'city': args[11], 'line1': args[13], 'country': args[10], 'state': args[12]}

            )
            customer_id = customer.id

            _charge = stripe.Charge.create(  # Создаем запрос на перевод
                customer=customer_id,
                amount=int(float(args[0]) * 100),
                currency="usd",
                description=args[8],
                statement_descriptor=args[9],
                receipt_email=args[6]
            )
        else:
            _charge = stripe.Charge.create(  # Создаем запрос на перевод
                source=token,
                amount=int(float(args[0]) * 100),
                currency="usd",
                description=args[8],
                statement_descriptor=args[9],
                receipt_email=args[6]
            )

        try:
            r_score = str(_charge.outcome.risk_score)
        except Exception as e:
            print(e)
            r_score = 'unavailable'

        resp = get_card_name(buffer[0]) + '\n' + \
               _charge.outcome.seller_message + '\n\nRisk level: ' + _charge.outcome.risk_level + \
               '\nRisk score: ' + r_score

        resp += check_zip_n_street(_charge)

        proxy_client.close()
        socks.setdefaultproxy(None)
        buffer = [None]
        return resp  # Возвращаем статус перевода, риски и сообщение

    except stripe.error.CardError as e:  # Обработка ошибок
        print(e)
        proxy_client.close()
        socks.setdefaultproxy(None)
        resp = get_error_message(buffer, e)
        buffer = [None]
        return resp

    except stripe.error.RateLimitError as e:
        print(e)
        proxy_client.close()
        socks.setdefaultproxy(None)
        resp = get_error_message(buffer, e)
        buffer = [None]
        return resp

    except stripe.error.InvalidRequestError as e:
        print(e)
        proxy_client.close()
        socks.setdefaultproxy(None)
        resp = get_error_message(buffer, e)
        buffer = [None]
        return resp

    except stripe.error.AuthenticationError as e:
        print(e)
        proxy_client.close()
        socks.setdefaultproxy(None)
        resp = get_error_message(buffer, e)
        buffer = [None]
        return resp

    except stripe.error.APIConnectionError as e:
        print(e)
        proxy_client.close()
        socks.setdefaultproxy(None)
        resp = get_error_message(buffer, e)
        buffer = [None]
        return resp

    except stripe.error.StripeError as e:
        print(e)
        proxy_client.close()
        socks.setdefaultproxy(None)
        resp = get_error_message(buffer, e)
        buffer = [None]
        return resp

    except Exception as e:
        print(e)
        proxy_client.close()
        socks.setdefaultproxy(None)
        resp = get_error_message(buffer, e)
        buffer = [None]
        return resp


if not set_new_proxy(def_proxy):
    def_proxy = [None, None, None]
    with open('proxy.txt', 'w') as f:
        f.write('')

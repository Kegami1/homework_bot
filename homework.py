import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
)
logger.addHandler(logging.StreamHandler())

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Пробуем отправить сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError:
        logger.error('Сообщение не было отрпавлено, что-то пошло не так')
    logger.info('Сообщение успешно отправлено')


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if api_answer.status_code != 200:
            logger.error('Ответ не получен')
            raise ConnectionError('Ответ не получен')
        return api_answer.json()

    except Exception as error:
        logger.error('Ответ от эндпоинта не получен')
        raise error


def check_response(response):
    """Проверяем ответ от эндпоинта."""
    my_homeworks = response['homeworks']
    if type(response) is not dict:
        logger.error('Некорректный тип данных response')
        raise TypeError('Некорректный тип данных response')
    if type(my_homeworks) is not list:
        logger.error('Некорректный тип данных у my_homeworks')
        raise KeyError('Некорректный тип данных у my_homeworks')
    elif response is None:
        raise KeyError('Пустой словарь')
    return my_homeworks


def parse_status(homework):
    """Получаем статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('Некорректный статус домашней работы')
        raise KeyError('Некорректный статус домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка обязательных переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID is not None:
        return True
    logger.critical('Отсутствуют обязательные переменные окружения')
    return False


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        raise KeyError('Отсутствуют необходимые данные')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)

            homework = check_response(response)
            if homework:
                status = parse_status(homework[0])
                send_message(bot, status)

            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

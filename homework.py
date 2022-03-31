import logging
import os
import sys
import time
from http import HTTPStatus

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


HOMEWORK_VERDICTS = {
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
        return False
    else:
        logger.info('Сообщение успешно отправлено')
        return True


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if api_answer.status_code != HTTPStatus.OK:
            answer_error = 'Ответ не получен'
            logger.error(answer_error)
            raise ConnectionError(answer_error)
        return api_answer.json()
    except Exception as error:
        logging.exception('Ответ от эндпоинта не получен')
        raise error


def check_response(response):
    """Проверяем ответ от эндпоинта."""
    if not isinstance(response, dict):
        dict_error = 'Некорректный тип данных response'
        logger.error(dict_error)
        raise TypeError(dict_error)
    if not isinstance(response['homeworks'], list):
        list_error = 'Некорректный тип данных у my_homeworks'
        logger.error(list_error)
        raise KeyError(list_error)
    if response is None:
        raise KeyError('Пустой словарь')
    return response['homeworks']


def parse_status(homework):
    """Получаем статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except Exception:
        status_error = 'Некорректный статус домашней работы'
        logger.error(status_error)
        raise KeyError(status_error)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка обязательных переменных окружения."""
    if (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID) is not None:
        return True
    logger.critical('Отсутствуют обязательные переменные окружения')
    return False


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        raise KeyError('Отсутствуют необходимые данные')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                status = parse_status(homework[0])
                if send_message(bot, status) is True:
                    last_error = ''
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            if last_error != error:
                message = f'Сбой в работе программы: {error}'
                if send_message(bot, message) is True:
                    last_error = error
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

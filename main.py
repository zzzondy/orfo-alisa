# импортируем библиотеки
from flask import Flask, request
import logging
import sqlite3
import random
# библиотека, которая нам понадобится для работы с JSON
import json

# создаём приложение
# мы передаём __name__, в нем содержится информация,
# в каком модуле мы находимся.
# В данном случае там содержится '__main__',
# так как мы обращаемся к переменной из запущенного модуля.
# если бы такое обращение, например,
# произошло внутри модуля logging, то мы бы получили 'logging'
app = Flask(__name__)
STARTED_GAME = False
WAITING_FOR_ANSWER = False
WAITING_FOR_CHOOSE_DIFFICULTY = False
GAME_WORDS = []
FIRST_ANSWER = False
WORD_INDEX = 0
COUNT = 0
DIFFICULTY = None
# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

# Создадим словарь, чтобы для каждой сессии общения
# с навыком хранились подсказки, которые видел пользователь.
# Это поможет нам немного разнообразить подсказки ответов
# (buttons в JSON ответа).
# Когда новый пользователь напишет нашему навыку,
# то мы сохраним в этот словарь запись формата
# sessionStorage[user_id] = {'suggests': ["Не хочу.", "Не буду.", "Отстань!" ]}
# Такая запись говорит, что мы показали пользователю эти три подсказки.
# Когда он откажется купить слона,
# то мы уберем одну подсказку. Как будто что-то меняется :)
sessionStorage = {}


@app.route('/post', methods=['POST'])
# Функция получает тело запроса и возвращает ответ.
# Внутри функции доступен request.json - это JSON,
# который отправила нам Алиса в запросе POST
def main():
    logging.info(f'Request: {request.json!r}')

    # Начинаем формировать ответ, согласно документации
    # мы собираем словарь, который потом при помощи
    # библиотеки json преобразуем в JSON и отдадим Алисе
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    # Отправляем request.json и response в функцию handle_dialog.
    # Она сформирует оставшиеся поля JSON, которые отвечают
    # непосредственно за ведение диалога
    handle_dialog(request.json, response)

    logging.info(f'Response:  {response!r}')

    # Преобразовываем в JSON и возвращаем
    return json.dumps(response)


def start_game(user_id, difficult):
    global GAME_WORDS
    connection = sqlite3.connect('data/words.db')
    cursor = connection.cursor()
    if difficult == 'easy':
        words = cursor.execute("""SELECT * FROM words ORDER BY RANDOM() LIMIT 10""").fetchall()
        GAME_WORDS = [word for word in words]
        change_buttons(GAME_WORDS, user_id, WORD_INDEX, start_flag=True)
    elif difficult == 'medium':
        words = cursor.execute("""SELECT * FROM words ORDER BY RANDOM() LIMIT 20""").fetchall()
        GAME_WORDS = [word for word in words]
        change_buttons(GAME_WORDS, user_id, WORD_INDEX, start_flag=True)
    else:
        words = cursor.execute("""SELECT * FROM words ORDER BY RANDOM() LIMIT 25""").fetchall()
        GAME_WORDS = [word for word in words]
        change_buttons(GAME_WORDS, user_id, WORD_INDEX, start_flag=True)
    print(len(GAME_WORDS))


def smart_game_finish(difficulty, count):
    if difficulty == 'easy' and count <= 5:
        return f"Ты набрал {count} очков. Это фигово."
    elif difficulty == 'easy' and 5 < count <= 9:
        return f"Ты набрал {count} очков. Это неплохо."
    elif difficulty == 'easy' and count == 10:
        return f"Ты набрал {count} очков. Это хорошо!!!"
    elif difficulty == 'medium' and count <= 5:
        return f"Ты набрал {count} очков. Это фигово."
    elif difficulty == 'medium' and 5 < count <= 10:
        return f"Ты набрал {count} очков. Это хорошо!"
    elif difficulty == 'medium' and 10 < count <= 17:
        return f"Ты набрал {count} очков. Это очень хорошо!"
    elif difficulty == 'medium' and 17 < count <= 20:
        return f"Ты набрал {count} очков. Это офигенно!"
    elif difficulty == 'high' and count <= 5:
        return f"Ты набрал {count} очков. Это фигово."
    elif difficulty == 'high' and 5 < count <= 10:
        return f"Ты набрал {count} очков. Это хорошо!"
    elif difficulty == 'high' and 10 < count <= 17:
        return f"Ты набрал {count} очков. Это очень хорошо!"
    elif difficulty == 'high' and 17 < count <= 19:
        return f"Ты набрал {count} очков. Это офигенно!"
    elif difficulty == 'high' and 19 < count <= 24:
        return f"Ты набрал {count} очков. Это замечательно!"
    elif difficulty == 'high' and count == 25:
        return f"Ты набрал {count} очков. Поздравляю, ты сдал ЕГЭ."


def check_answer(words, index, req, start_flag=False):
    if not start_flag:
        if req['request']['original_utterance'] == words[index][1]:
            return True
        return False
    else:
        if req['request']['original_utterance'].lower() == 'да.':
            return True
        return False


def random_words(words, index):
    temp = [*words[index][1:]]
    random.shuffle(temp)
    return temp[::]


def change_buttons(words, user_id, index, start_flag=False, flag_difficulty=False):
    global sessionStorage, GAME_WORDS
    if flag_difficulty:
        sessionStorage[user_id] = {
            'suggests': [
                'Легкая.', 'Средняя.', 'Сложная.', 'Выйти из игры.'
            ]
        }
    elif not start_flag:
        temp = [*words[index][1:]]
        random.shuffle(temp)
        random_buttons = temp[::]
        sessionStorage[user_id] = {
            'suggests': [
                random_buttons[0],
                random_buttons[1]
            ]
        }
    else:
        sessionStorage[user_id] = {
            'suggests': [
                'Да.', 'Нет.'
            ]
        }


def handle_dialog(req, res):
    global STARTED_GAME, DIFFICULTY, WAITING_FOR_ANSWER, WORD_INDEX, COUNT, FIRST_ANSWER, WAITING_FOR_CHOOSE_DIFFICULTY, \
        GAME_WORDS
    user_id = req['session']['user_id']

    if req['session']['new']:
        STARTED_GAME = False
        WAITING_FOR_ANSWER = False
        WAITING_FOR_CHOOSE_DIFFICULTY = False
        GAME_WORDS = []
        FIRST_ANSWER = False
        WORD_INDEX = 0
        COUNT = 0
        # Это новый пользователь.
        # Инициализируем сессию и поприветствуем его.
        # Запишем подсказки, которые мы ему покажем в первый раз
        # Заполняем текст ответа

        res['response'][
            'text'] = 'Привет! Ты попал на орфоэпическую игру и твоя задача как можно' \
                      ' больше раз угадать правильное произношение слов. Ты готов?'
        change_buttons(GAME_WORDS, user_id, WORD_INDEX, start_flag=True)
        res['response']['buttons'] = get_suggests(user_id)
        return

    # Сюда дойдем только, если пользователь не новый,
    # и разговор с Алисой уже был начат
    # Обрабатываем ответ пользователя.
    # В req['request']['original_utterance'] лежит весь текст,
    # что нам прислал пользователь
    # Если он написал 'ладно', 'куплю', 'покупаю', 'хорошо',
    # то мы считаем, что пользователь согласился.
    # Подумайте, всё ли в этом фрагменте написано "красиво"?
    if WAITING_FOR_CHOOSE_DIFFICULTY:
        if req['request']['original_utterance'] == 'Легкая.':
            start_game(user_id, 'easy')
            words = random_words(GAME_WORDS, WORD_INDEX)
            res['response']['text'] = f"Вы пошли по легкому пути. Ну ладно. Вот вам 10 слов." \
                                      f" И первой парой у нас будет: {words[0]} и {words[1]}"
            change_buttons(GAME_WORDS, user_id, 0)
            res['response']['buttons'] = get_suggests(user_id)
            WAITING_FOR_ANSWER = True
            WAITING_FOR_CHOOSE_DIFFICULTY = False
            STARTED_GAME = True
            DIFFICULTY = 'easy'
        elif req['request']['original_utterance'] == 'Средняя.':
            start_game(user_id, 'medium')
            words = random_words(GAME_WORDS, WORD_INDEX)
            res['response'][
                'text'] = f'У-у-у, а вы красаучик. Вот вам 20 слов. И первой парой у нас будет: {words[0]} и {words[1]}'
            change_buttons(GAME_WORDS, user_id, 0)
            res['response']['buttons'] = get_suggests(user_id)
            WAITING_FOR_ANSWER = True
            WAITING_FOR_CHOOSE_DIFFICULTY = False
            STARTED_GAME = True
            DIFFICULTY = 'medium'
        elif req['request']['original_utterance'] == 'Сложная.':
            start_game(user_id, 'high')
            words = random_words(GAME_WORDS, WORD_INDEX)
            res['response'][
                'text'] = f'А вы самоуверенный. Вот вам 25 слов. И первой парой у нас будет: {words[0]} и {words[1]}'
            change_buttons(GAME_WORDS, user_id, 0)
            res['response']['buttons'] = get_suggests(user_id)
            WAITING_FOR_ANSWER = True
            WAITING_FOR_CHOOSE_DIFFICULTY = False
            STARTED_GAME = True
            DIFFICULTY = 'high'
        elif req['request']['original_utterance'] == 'Выйти из игры.':
            res['response']['text'] = f'Слабак!'
            STARTED_GAME = False
            WAITING_FOR_ANSWER = False
            WAITING_FOR_CHOOSE_DIFFICULTY = False
            GAME_WORDS = []
            FIRST_ANSWER = False
            WORD_INDEX = 0
            COUNT = 0
            res['response']['end_session'] = True
        return
    if not STARTED_GAME:
        if req['request']['original_utterance'].lower() == 'да.':
            # Пользователь согласился, прощаемся.
            res['response'][
                'text'] = 'Отлично! Для начала выберите сложность: легкая, средняя,' \
                          ' тяжелая. Или вы можете выйти из игры.'
            change_buttons(GAME_WORDS, user_id, 0, flag_difficulty=True)
            res['response']['buttons'] = get_suggests(user_id, difficult_suggest=True)
            WAITING_FOR_CHOOSE_DIFFICULTY = True
            return
        else:
            res['response'][
                'text'] = f"Ну и пошел ты!"
            STARTED_GAME = False
            WAITING_FOR_ANSWER = False
            WAITING_FOR_CHOOSE_DIFFICULTY = False
            GAME_WORDS = []
            FIRST_ANSWER = False
            WORD_INDEX = 0
            COUNT = 0
            res['response']['end_session'] = True
            return
    if STARTED_GAME:
        if WAITING_FOR_ANSWER:
            if check_answer(GAME_WORDS, WORD_INDEX, req):
                WORD_INDEX += 1
                COUNT += 1
                try:
                    words = random_words(GAME_WORDS, WORD_INDEX)
                    res['response'][
                        'text'] = f"Ты отгадал! Всего слов {len(GAME_WORDS) - WORD_INDEX}. Твой счет: {COUNT}." \
                                  f" Идем дальше: {words[0]} и" \
                                  f" {words[1]}"
                    change_buttons(GAME_WORDS, user_id, WORD_INDEX)
                    res['response']['buttons'] = get_suggests(user_id)
                except IndexError:
                    res['response'][
                        'text'] = smart_game_finish(DIFFICULTY, COUNT)
                    STARTED_GAME = False
                    res['response']['end_session'] = True
            else:
                WORD_INDEX += 1
                try:
                    words = random_words(GAME_WORDS, WORD_INDEX)
                    res['response'][
                        'text'] = f"Увы! Ты не удагал. Всего слов {len(GAME_WORDS) - WORD_INDEX}. Твой счет: {COUNT}." \
                                  f" Идем дальше: {words[0]} и" \
                                  f" {words[1]}"
                    change_buttons(GAME_WORDS, user_id, WORD_INDEX)
                    res['response']['buttons'] = get_suggests(user_id)
                except IndexError:
                    res['response'][
                        'text'] = smart_game_finish(DIFFICULTY, COUNT)
                    STARTED_GAME = False
                    res['response']['end_session'] = True
    return


# Функция возвращает две подсказки для ответа.
def get_suggests(user_id, difficult_suggest=False):
    global sessionStorage
    session = sessionStorage[user_id]

    # Выбираем две первые подсказки из массива.
    if not difficult_suggest:
        suggests = [
            {'title': suggest, 'hide': True}
            for suggest in session['suggests'][:2]
        ]
    else:
        suggests = [
            {'title': suggest, 'hide': True}
            for suggest in session['suggests'][:4]
        ]
    sessionStorage = {}
    return suggests


if __name__ == '__main__':
    app.run()

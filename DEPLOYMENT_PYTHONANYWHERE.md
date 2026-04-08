# Развертывание Django проекта на PythonAnywhere

## Шаг 1: Регистрация на PythonAnywhere

1. Перейдите на https://www.pythonanywhere.com/
2. Нажмите "Create account" и зарегистрируйтесь (бесплатный тариф "Beginner")
3. Подтвердите email

## Шаг 2: Загрузка проекта на PythonAnywhere

### Вариант А: Через GitHub (рекомендуется)

1. Создайте репозиторий на GitHub и загрузите туда проект
2. В PythonAnywhere перейдите в "Consoles" -> "Bash"
3. Выполните:
```bash
git clone https://github.com/ВАШ_ЮЗЕРНЕЙМ/ВАШ_РЕПОЗИТОРИЙ.git
cd chinilkin
```

### Вариант Б: Через веб-интерфейс

1. В PythonAnywhere перейдите в "Files"
2. Загрузите все файлы проекта через кнопку "Upload files"
3. Или создайте папку и загрузите архив

## Шаг 3: Создание виртуального окружения

В Bash консоли выполните:
```bash
cd chinilkin
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Шаг 4: Настройка базы данных

Так как используется SQLite, просто скопируйте существующий файл db.sqlite3 или создайте новую базу:

```bash
# Если переносите существующую базу - просто скопируйте файл db.sqlite3
# Если создаете новую базу:
python manage.py migrate
```

## Шаг 5: Настройка веб-приложения

1. В PythonAnywhere перейдите в "Web" tab
2. Нажмите "Add a new web app"
3. Выберите "Manual configuration" (включая Python 3.11)
4. В разделе "Source code" укажите путь: `/home/ВАШ_ЮЗЕРНЕЙМ/chinilkin`
5. В разделе "WSGI configuration file" нажмите редактировать и замените содержимое на:

```python
import os
import sys

path = '/home/ВАШ_ЮЗЕРНЕЙМ/chinilkin'
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chinilkin.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

6. В разделе "Virtualenv" укажите путь: `/home/ВАШ_ЮЗЕРНЕЙМ/chinilkin/venv`
7. В разделе "Static files" добавьте:
   - URL: `/static/`
   - Directory: `/home/ВАШ_ЮЗЕРНЕЙМ/chinilkin/tickets/static`

## Шаг 6: Настройка переменных окружения (опционально)

В "Web" -> "Variables" добавьте:
```
DEBUG=False
ALLOWED_HOSTS=ВАШ_ЮЗЕРНЕЙМ.pythonanywhere.com
SECRET_KEY=ВАШ_НОВЫЙ_СЕКРЕТНЫЙ_КЛЮЧ
```

## Шаг 7: Сбор статических файлов

В Bash консоли:
```bash
cd chinilkin
source venv/bin/activate
python manage.py collectstatic
```

## Шаг 8: Перезагрузка веб-приложения

В "Web" tab нажмите кнопку "Reload"

## Шаг 9: Проверка

Ваш сайт будет доступен по адресу:
`https://ВАШ_ЮЗЕРНЕЙМ.pythonanywhere.com/`

## Важные примечания

1. **SECRET_KEY**: Для продакшена замените секретный ключ в settings.py на новый
2. **DEBUG=False**: Обязательно отключите DEBUG в продакшене
3. **ALLOWED_HOSTS**: Добавьте ваш домен в ALLOWED_HOSTS
4. **Email настройки**: Если используете Gmail, убедитесь что App Password работает
5. **SQLite**: PythonAnywhere поддерживает SQLite, но для продакшена лучше PostgreSQL (требует платного тарифа)

## Решение проблем

Если сайт не работает:
1. Проверьте логи в "Web" -> "Log files"
2. Убедитесь что все зависимости установлены: `pip list`
3. Проверьте что миграции применены: `python manage.py showmigrations`
4. Проверьте права доступа к файлам базы данных

## Бесплатные ограничения

- 1 веб-приложение
- 1 консоль одновременно
- Ограниченное время CPU в месяц (для учебного проекта достаточно)
- SQLite поддерживается на бесплатном тарифе

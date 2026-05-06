# Task Tracker API (simplified)

В этом репозитории папка `tasks` упрощена: в ней остались только
- `admin.py`
- `apps.py`
- `models.py`
- `serializers.py`
- `urls.py`
- `utils.py`

Запуск локально (в каталоге django_endpoints):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Документация по API доступна по `/swagger/` и `/redoc/` (если установлены зависимости).

Примечание: логика permissions и константы статусов/приоритетов теперь находятся в `tasks/utils.py`.

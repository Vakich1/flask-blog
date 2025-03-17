from app import app, db  # Импортируешь приложение и объект db

with app.app_context():  # Создаешь контекст приложения
    db.create_all()  # Создаешь все таблицы, которые описаны в моделях
    print("Tables created successfully.")

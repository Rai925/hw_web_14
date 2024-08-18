from db import Base, engine

def create_tables():
    # Створюємо таблиці в базі даних
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    create_tables()
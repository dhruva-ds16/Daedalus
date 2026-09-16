from app.database.base import Base
from app.database.session import engine


def initialize_database():
    from app.database import models

    Base.metadata.create_all(
        bind=engine
    )
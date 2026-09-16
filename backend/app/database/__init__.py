def initialize_database():
    """
    Database schema is managed exclusively by Alembic.

    This function intentionally performs no schema creation.
    It remains as an application startup hook so database
    initialization behavior can be extended later if needed.
    """
    pass
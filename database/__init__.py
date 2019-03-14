# from sqlalchemy.orm import sessionmaker
# from sqlalchemy import create_engine
# from sqlalchemy_utils import database_exists, create_database
# from database.cobhamdb import CobhamDB
#
# db_path = "sqlite:///cobham_db.db"
# engine = create_engine(db_path)
# if not database_exists(engine.url):
#     session = CobhamDB(engine)
#     session.create_db()
#
# def create_db(self):
#     create_database(self.engine.url)
#
# Session = sessionmaker(bind=engine)
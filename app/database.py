from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os


load_dotenv()              #load environment variables}

DATABASE_URL= os.getenv("DB_URL")      #read database url from env file

engine= create_engine(DATABASE_URL)    #creating a SQLAlchemy  database engine 

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
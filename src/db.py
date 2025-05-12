from sqlalchemy import create_engine
from .config import DB_URI

engine = create_engine(DB_URI, pool_pre_ping=True)

def get_engine():
    return engine

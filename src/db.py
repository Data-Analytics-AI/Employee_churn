from sqlalchemy import create_engine
from .config import DB_URI

#engine = create_engine(DB_URI, pool_pre_ping=True)

import ssl
#from sqlalchemy import create_engine

ssl_args = {
    "ssl": {
        "ssl_disabled": False
    }
}

engine = create_engine(DB_URI, pool_pre_ping=True,
    connect_args=ssl_args
)

def get_engine():
    return engine

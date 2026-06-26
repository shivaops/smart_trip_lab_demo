from __future__ import annotations

import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    """Return a new DB connection to ARS schema.

    Reads from .env:
      ARS_DB_HOST, ARS_DB_PORT, ARS_DB_USER, ARS_DB_PASSWORD, ARS_DB_NAME
    """

    return pymysql.connect(
        host=os.getenv("ARS_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("ARS_DB_PORT", "3306")),
        user=os.getenv("ARS_DB_USER", "root"),
        password=os.getenv("ARS_DB_PASSWORD", ""),
        database=os.getenv("ARS_DB_NAME", "ars"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

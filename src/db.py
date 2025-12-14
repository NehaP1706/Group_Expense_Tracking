from fastapi import Request
import mysql.connector.aio as mysql_connector
from mysql.connector.aio import PooledMySQLConnection, MySQLConnectionAbstract
from mysql.connector.aio.abstracts import MySQLCursorAbstract

from .config import get_config

Db = PooledMySQLConnection | MySQLConnectionAbstract
Cur = MySQLCursorAbstract


async def connect_to_db():
    config = get_config()
    conn = await mysql_connector.connect(
        host=config.mysql_host,
        port=config.mysql_port,
        database=config.mysql_db,
        user=config.mysql_user,
        password=config.mysql_pass,
    )
    print("Connected to Database!")
    return conn


async def get_db(req: Request):
    db: Db = req.app.state.db
    cur = await db.cursor(dictionary=True)
    yield cur
    await cur.close()

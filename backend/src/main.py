import asyncio
import secrets

import argon2.exceptions
import asyncpg
from aiohttp import web
from argon2 import PasswordHasher

routes = web.RouteTableDef()


class DbConnectionManager:
    def __init__(self, *, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None

    async def get_connection(self) -> asyncpg.connection.Connection:
        if self.conn is None:
            self.conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
        return self.conn

    async def close_connection(self):
        if self.conn is not None:
            await self.conn.close()
            self.conn = None


connection_manager = DbConnectionManager(
    host="db.hwpdbfudsrjbdofrgpgv.supabase.co",
    port=5432,
    user="postgres",
    password="mCKpiZhdW6^G%FVcjd2TiMQs",
    database="postgres",
)


def json_error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"error": message}, status=status)


@routes.post("/v1/auth/register")
async def auth_register(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "username" not in parameters:
        return json_error("username is required")
    if "password" not in parameters:
        return json_error("password is required")

    connection = await connection_manager.get_connection()

    exists = await connection.fetchval("""
        select exists(select 1 from "user" where username = $1)
    """, parameters["username"])
    if exists:
        return json_error("username already exists")

    password_hash = PasswordHasher().hash(parameters.get("password"))
    insert = await connection.fetchrow("""
        insert into "user" (username, password) values ($1, $2)
        returning id, username
    """, parameters["username"], password_hash)

    return web.json_response({
        "id": insert.get("id"),
        "username": insert.get("username"),
    })


@routes.post("/v1/auth/login")
async def auth_login(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "username" not in parameters:
        return json_error("username is required")
    if "password" not in parameters:
        return json_error("password is required")

    connection = await connection_manager.get_connection()

    exists = await connection.fetchval("""
        select exists(select 1 from "user" where username = $1)
    """, parameters["username"])
    if not exists:
        return json_error("username does not exist")

    user = await connection.fetchrow("""
        select id, username, password
        from "user"
        where username = $1
    """, parameters["username"])

    try:
        PasswordHasher().verify(
            user.get("password"),
            parameters.get("password")
        )
    except argon2.exceptions.VerifyMismatchError:
        return json_error("password is incorrect")

    token = secrets.token_hex(32)

    await connection.fetchrow(
        """
            insert into session ("user", token, ip, user_agent)
            values ($1, $2, $3, $4)
        """,
        user.get("id"),
        token,
        request.remote,
        request.headers.get("User-Agent")
    )

    return web.json_response({
        "username": user.get("username"),
        "token": token,
    })


@routes.get("/v1/debug/users")
async def debug(request: web.Request) -> web.Response:
    conn = await connection_manager.get_connection()

    row = await conn.fetch("""
        select * from "user"
    """)

    return web.json_response(
        [row.get("username") for row in row]
    )


def main():
    app = web.Application()
    app.add_routes(routes)

    async def on_shutdown(_):
        await connection_manager.close_connection()

    app.on_shutdown.append(on_shutdown)

    web.run_app(app, loop=asyncio.get_event_loop())


if __name__ == '__main__':
    main()

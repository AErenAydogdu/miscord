import asyncio
import secrets
import datetime
import string

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


def serialize_record(record: asyncpg.Record) -> dict:
    record = dict(record)
    for key, value in record.items():
        if isinstance(value, datetime.datetime):
            record[key] = value.isoformat()
    return record


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


@routes.post("/v1/server")
async def server_create(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")
    if "name" not in parameters:
        return json_error("name is required")
    if "description" not in parameters:
        return json_error("description is required")

    connection = await connection_manager.get_connection()

    user = await connection.fetchrow("""
        select u.id as id
        from "user" u left join "session" s on u.id = s."user"
        where s.token = $1
    """, request.headers.get("Authorization"))

    if not user:
        return json_error("invalid token")

    server = await connection.fetchrow("""
        insert into server (name, description, owner)
        values ($1, $2, $3)
        returning *
    """, parameters["name"], parameters["description"], user.get("id"))

    return web.json_response(serialize_record(server))


@routes.delete("/v1/server")
async def server_delete(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")
    if "id" not in parameters:
        return json_error("id is required")

    connection = await connection_manager.get_connection()

    user = await connection.fetchrow("""
        select u.id as id
        from "user" u left join "session" s on u.id = s."user"
        where s.token = $1
    """, request.headers.get("Authorization"))

    if not user:
        return json_error("invalid token")

    server = await connection.fetchrow("""
        select owner
        from server
        where id = $1
    """, parameters.get("id"))

    if not server:
        return json_error("server not found")

    if server.get("owner") != user.get("id"):
        return json_error("you are not the owner of this server")

    server = await connection.fetchrow("""
        delete from server where id = $1
        returning *
    """, parameters["id"])

    return web.json_response(serialize_record(server))


@routes.patch("/v1/server")
async def server_patch(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")
    if "id" not in parameters:
        return json_error("id is required")

    connection = await connection_manager.get_connection()

    user = await connection.fetchrow("""
        select u.id as id
        from "user" u left join "session" s on u.id = s."user"
        where s.token = $1
    """, request.headers.get("Authorization"))

    server = await connection.fetchrow("""
        select name, description, owner
        from server
        where id = $1
    """, parameters["id"])

    if not server:
        return json_error("server not found")

    if server.get("owner") != user.get("id"):
        return json_error("you are not the owner of this server")

    new_name = parameters.get("name") or server.get("name")
    new_description = parameters.get("description") or server.get("description")

    server = await connection.fetchrow("""
        update server
        set name = $1, description = $2
        where id = $3
        returning *
    """, new_name, new_description, parameters["id"])

    return web.json_response(serialize_record(server))


@routes.get("/v1/server")
async def server_get(request: web.Request) -> web.Response:
    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")

    connection = await connection_manager.get_connection()

    user = await connection.fetchrow("""
        select u.id as id
        from "user" u left join "session" s on u.id = s."user"
        where s.token = $1
    """, request.headers.get("Authorization"))

    if not user:
        return json_error("invalid token")

    servers = await connection.fetch("""
        select *
        from server
        where owner = $1
    """, user.get("id"))

    return web.json_response({
        "owner": [
            serialize_record(server)
            for server in servers
        ]
    })

@routes.post("/v1/invite")
async def create_invite(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")
    if "server" not in parameters:
        return json_error("server is required")

    connection = await connection_manager.get_connection()

    user = await connection.fetchrow("""
        select u.id as id
        from "user" u left join "session" s on u.id = s."user"
        where s.token = $1
    """, request.headers.get("Authorization"))

    if not user:
        return json_error("invalid token")

    server = await connection.fetchrow("""
        select id, owner
        from server
        where id = $1
    """, parameters.get("server"))

    if not server:
        return json_error("server not found")

    if server.get("owner") != user.get("id"):
        return json_error("you are not the owner of this server")

    code = "".join(
        [
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(6)
        ]
    )

    invite = await connection.fetchrow("""
        insert into invite (server, code)
        values ($1, $2)
        returning *
    """, parameters.get("server"), code)

    return web.json_response(serialize_record(invite))


def main():
    app = web.Application()
    app.add_routes(routes)

    async def on_shutdown(_):
        await connection_manager.close_connection()

    app.on_shutdown.append(on_shutdown)

    web.run_app(app, loop=asyncio.get_event_loop())


if __name__ == '__main__':
    main()

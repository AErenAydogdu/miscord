import asyncio
import secrets
import datetime
import string

import aiohttp_cors
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
        self.connections = []

    async def get_connection(self) -> asyncpg.connection.Connection:
        connection = await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
        )
        self.connections.append(connection)
        return connection

    async def close_connections(self):
        for connection in self.connections:
            await connection.close()
        self.connections = []


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
        "id": user.get("id"),
        "username": user.get("username"),
        "token": token,
    })


@routes.post("/v1/auth/logout")
async def auth_logout(request: web.Request) -> web.Response:
    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")

    connection = await connection_manager.get_connection()

    await connection.fetchrow("""
        delete from session
        where token = $1
    """, request.headers.get("Authorization"))

    return web.Response(status=204)


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

    await connection.execute("""
        insert into member ("user", server)
        values ($1, $2)
    """, user.get("id"), server.get("id"))

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

    member_servers = await connection.fetch("""
        select s.*
        from member m
        join server s on m.server = s.id
        where m."user" = $1
    """, user.get("id"))


    return web.json_response([
        serialize_record(server)
        for server in member_servers
    ])


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


@routes.post("/v1/member")
async def join_server(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")
    if "code" not in parameters:
        return json_error("code is required")

    connection = await connection_manager.get_connection()

    user = await connection.fetchrow("""
        select u.id as id
        from "user" u left join "session" s on u.id = s."user"
        where s.token = $1
    """, request.headers.get("Authorization"))

    if not user:
        return json_error("invalid token")

    invite = await connection.fetchrow("""
        select server
        from invite
        where code = $1
    """, parameters.get("code"))

    if not invite:
        return json_error("invite not found")

    server = await connection.fetchrow("""
        select *
        from server
        where id = $1
    """, invite.get("server"))

    if not server:
        return json_error("server not found")

    await connection.execute("""
        insert into member ("user", server)
        values ($1, $2)
    """, user.get("id"), server.get("id"))

    return web.json_response(serialize_record(server))


@routes.delete("/v1/member")
async def leave_server(request: web.Request) -> web.Response:
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

    member = await connection.fetchrow("""
        select 1
        from member
        where "user" = $1 and server = $2
    """, user.get("id"), parameters.get("server"))
    if not member:
        return json_error("not a member of this server")

    server = await connection.fetchrow("""
        select id
        from server
        where id = $1
    """, parameters.get("server"))

    if not server:
        return json_error("server not found")

    await connection.execute("""
        delete from member
        where "user" = $1 and server = $2
    """, user.get("id"), server.get("id"))

    return web.json_response(serialize_record(server))


@routes.post("/v1/message")
async def create_message(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")
    if "server" not in parameters:
        return json_error("server is required")
    if "content" not in parameters:
        return json_error("content is required")

    connection = await connection_manager.get_connection()

    user = await connection.fetchrow("""
        select u.id as id
        from "user" u left join "session" s on u.id = s."user"
        where s.token = $1
    """, request.headers.get("Authorization"))

    if not user:
        return json_error("invalid token")

    member = await connection.fetchrow("""
        select 1
        from member
        where "user" = $1 and server = $2
    """, user.get("id"), parameters.get("server"))
    if not member:
        return json_error("not a member of this server")

    message = await connection.fetchrow("""
        insert into message (author, server, content)
        values ($1, $2, $3)
        returning *
    """, user.get("id"), parameters.get("server"), parameters.get("content"))

    return web.json_response(serialize_record(message))


@routes.patch("/v1/message")
async def edit_message(request: web.Request) -> web.Response:
    parameters = await request.json()

    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")
    if "content" not in parameters:
        return json_error("content is required")
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

    message = await connection.fetchrow("""
        select author
        from message
        where id = $1
    """, parameters.get("id"))

    if not message:
        return json_error("message not found")

    if message.get("member") != user.get("id"):
        return json_error("you are not the owner of this message")

    member = await connection.fetchrow("""
        select 1
        from member
        where "user" = $1 and server = $2
    """, user.get("id"), parameters.get("server"))
    if not member:
        return json_error("not a member of this server")

    message = await connection.fetchrow("""
        update message
        set content = $1
        where id = $2
        returning *
    """, parameters.get("content"), parameters.get("id"))

    return web.json_response(serialize_record(message))


@routes.delete("/v1/message")
async def delete_message(request: web.Request) -> web.Response:
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

    message = await connection.fetchrow("""
        select author
        from message
        where id = $1
    """, parameters.get("id"))

    if not message:
        return json_error("message not found")

    if message.get("member") != user.get("id"):
        return json_error("you are not the owner of this message")

    member = await connection.fetchrow("""
        select 1
        from member
        where "user" = $1 and server = $2
    """, user.get("id"), parameters.get("server"))
    if not member:
        return json_error("not a member of this server")

    message = await connection.fetchrow("""
        delete from message
        where id = $1
        returning *
    """, parameters.get("id"))

    return web.json_response(serialize_record(message))


@routes.get("/v1/message")
async def list_message(request: web.Request) -> web.Response:
    if "Authorization" not in request.headers:
        return json_error("missing Authorization header")

    if "server" not in request.query:
        return json_error("server is required")
    server_id = int(request.query["server"])

    if "limit" not in request.query:
        return json_error("limit is required")
    limit = int(request.query["limit"])

    if "offset" not in request.query:
        return json_error("offset is required")
    offset = int(request.query["offset"])

    connection = await connection_manager.get_connection()

    user = await connection.fetchrow("""
        select u.id as id
        from "user" u left join "session" s on u.id = s."user"
        where s.token = $1
    """, request.headers.get("Authorization"))

    if not user:
        return json_error("invalid token")

    member = await connection.fetchrow("""
        select 1
        from member
        where "user" = $1 and server = $2
    """, user.get("id"), server_id)
    if not member:
        return json_error("not a member of this server")

    messages = await connection.fetch("""
        select m.*, u.username as username
        from message m
        right join "user" u on m.author = u.id
        where m.server = $1
        order by m.id desc
        limit $2 offset $3
    """, server_id, limit, offset)

    return web.json_response({
        "messages": [
            serialize_record(message)
            for message in messages
        ]
    })


def main():
    app = web.Application()
    app.add_routes(routes)

    resource_options = {
            "http://localhost:5173": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                allow_headers="*",
                allow_methods="*",
            )
        }

    cors = aiohttp_cors.setup(app, defaults=resource_options)

    for route in list(app.router.routes()):
        cors.add(route, resource_options)

    async def on_shutdown(_):
        await connection_manager.close_connections()

    app.on_shutdown.append(on_shutdown)

    web.run_app(app, loop=asyncio.get_event_loop())


if __name__ == '__main__':
    main()

from json import load
from logging import getLogger
from uuid import uuid4

from aiohttp import web
from argon2 import PasswordHasher
from motor.motor_asyncio import AsyncIOMotorClient

from utils import (
    ADMIN_USER_DISPLAY_FORMAT,
    configure_logger,
    User,
    Image,
    BASE_HTML_TEMPLATE,
)

with open("config.json", "r") as f:
    config = load(f)

password_hasher = PasswordHasher()

logger = getLogger(__name__)

client = AsyncIOMotorClient(config["mongo_url"])
db = client["main_application"]
auth_db = db["auth"]
image_db = db["images"]
sessions = db["sessions"]

app = web.Application(logger=logger)

routes = web.RouteTableDef()

configure_logger(logger)


async def create_admin_user():
    """Create an admin user if no users exist"""
    if await auth_db.count_documents({}) == 0:
        print("Creating admin user...")
        password = uuid4().hex
        user = await User.create(
            username="admin",
            email="admin@localhost",
            password=password,
            admin=True,
            quota=-1,
            auth_db=auth_db,
            password_hasher=password_hasher,
        )
        print(ADMIN_USER_DISPLAY_FORMAT.format(user=user, password=password))


@routes.get("/api")
async def get_health(request):
    return web.json_response({"status": "ok"})


@routes.post("/auth/signup")
async def signup(request: web.Request) -> web.Response:
    """Sign up a user."""
    data = await request.post()
    username = data["username"]
    email = data["email"]
    password = data["password"]
    if await auth_db.find_one({"_username": username.lower()}):
        return web.json_response({"error": True, "message": "Username taken."})
    if await auth_db.find_one({"_email": email.lower()}):
        return web.json_response({"error": True, "message": "Email already in use."})

    await User.create(
        username, email, password, auth_db, password_hasher=password_hasher
    )

    return web.json_response({"error": False, "message": "User created."})


@routes.post("/auth/login")
async def login(request: web.Request) -> web.Response:
    data = await request.post()
    username = data["username"]
    password = data["password"]

    user = await auth_db.find_one(
        {"$or": [{"_username": username.lower()}, {"_email": username.lower()}]}
    )

    if not user:
        return web.json_response({"error": True, "message": "User not found."})

    if not password_hasher.verify(user["password"], password):
        return web.json_response(
            {"error": True, "message": "Invalid Username/Password."}
        )

    session = await sessions.insert_one({"user_id": user["id"], "token": uuid4().hex})

    return web.json_response(
        {"error": False, "message": "Logged in.", "token": session["token"]}
    )


@routes.get("/auth/accounts")
async def get_accounts(request: web.Request) -> web.Response:
    token = request.headers.get("Authorization")
    if not token:
        return web.json_response(
            {"error": True, "message": "No token provided."}, status=401
        )

    session = await sessions.find_one({"token": token})

    if not session:
        return web.json_response(
            {"error": True, "message": "Invalid token."}, status=403
        )

    user = await auth_db.find_one({"id": session["user_id"]})

    if not user["admin"]:
        return web.json_response(
            {"error": True, "message": "You are not an admin."}, status=403
        )

    users = [user async for user in auth_db.find({})]

    return web.json_response({"error": False, "users": users})

@routes.patch("/auth/account")
async def update_account(request: web.Request) -> web.Response:
    token = request.headers.get("Authorization")
    if not token:
        return web.json_response(
            {"error": True, "message": "No token provided."}, status=401
        )

    session = await sessions.find_one({"token": token})

    if not session:
        return web.json_response(
            {"error": True, "message": "Invalid token."}, status=403
        )

    user = await auth_db.find_one({"id": session["user_id"]})

    data = await request.post()

    if "username" in data:
        if await auth_db.find_one({"_username": data["username"].lower()}):
            return web.json_response(
                {"error": True, "message": "Username taken."}, status=400
            )
        user["username"] = data["username"]

    if "email" in data:
        if await auth_db.find_one({"_email": data["email"].lower()}):
            return web.json_response(
                {"error": True, "message": "Email already in use."}, status=400
            )
        user["email"] = data["email"]

    if "password" in data:
        user["password"] = password_hasher.hash(data["password"])

    if "quota" in data and user["admin"] is True:
        user["quota"] = int(data["quota"])

    await auth_db.update_one({"id": user["id"]}, {"$set": user})

    return web.json_response(
        {"error": False, "message": "Account updated.", "user": user}
    )


@routes.delete("/auth/account")
async def delete_account(request: web.Request) -> web.Response:
    token = request.headers.get("Authorization")
    if not token:
        return web.json_response(
            {"error": True, "message": "No token provided."}, status=401
        )

    session = await sessions.find_one({"token": token})

    if not session:
        return web.json_response(
            {"error": True, "message": "Invalid token."}, status=403
        )

    user = await auth_db.find_one({"id": session["user_id"]})

    await auth_db.delete_one({"id": user["id"]})

    return web.json_response({"error": False, "message": "Account deleted."})


@routes.delete("/admin/auth/account")
async def delete_account_as_admin(request: web.Request) -> web.Response:
    token = request.headers.get("Authorization")
    if not token:
        return web.json_response(
            {"error": True, "message": "No token provided."}, status=401
        )

    session = await sessions.find_one({"token": token})

    if not session:
        return web.json_response(
            {"error": True, "message": "Invalid token."}, status=403
        )

    user = await auth_db.find_one({"id": session["user_id"]})

    if not user["admin"]:
        return web.json_response(
            {"error": True, "message": "You are not an admin."}, status=403
        )

    data = await request.post()

    if "username" in data:
        user = await auth_db.find_one({"_username": data["username"].lower()})
    elif "email" in data:
        user = await auth_db.find_one({"_email": data["email"].lower()})
    else:
        return web.json_response(
            {"error": True, "message": "No username or email provided."}, status=400
        )

    await auth_db.delete_one(user)

    return web.json_response({"error": False, "message": "Account deleted."})


@routes.delete("/auth/logout")
async def logout(request: web.Request) -> web.Response:
    token = request.headers.get("Authorization")
    if not token:
        return web.json_response(
            {"error": True, "message": "No token provided."}, status=401
        )

    session = await sessions.find_one({"token": token})

    if not session:
        return web.json_response(
            {"error": True, "message": "Invalid token."}, status=403
        )

    await sessions.delete_one(session)

    return web.json_response({"error": False, "message": "Logged out."})


@routes.post("/images/upload")
async def upload_image(request: web.Request) -> web.Response:
    token = request.headers.get("Authorization")
    if not token:
        return web.json_response(
            {"error": True, "message": "No token provided."}, status=401
        )

    session = await sessions.find_one({"token": token})

    if not session:
        return web.json_response(
            {"error": True, "message": "Invalid token."}, status=403
        )

    user = await auth_db.find_one({"id": session["user_id"]})

    data = await request.multipart()
    file_field = await data.next()
    filename = file_field.filename

    if not filename or not file_field:
        return web.json_response(
            {"error": True, "message": "No file provided."}, status=400
        )

    if not filename.endswith((".png", ".jpg", ".jpeg", ".gif")):
        return web.json_response(
            {"error": True, "message": "Invalid file extension."}, status=400
        )

    if not file_field.content_type.startswith("image/"):
        return web.json_response(
            {"error": True, "message": "Invalid file type."}, status=400
        )

    file_data = await file_field.read()

    _images = [image async for image in image_db.find({"owner_id": user["id"]})]
    images = [len(image["data"]) for image in _images]
    used_quota = len(file_data) + sum(images)

    if used_quota > user["quota"] and user["quota"] != -1:
        return web.json_response(
            {"error": True, "message": "File too large."}, status=413
        )

    if len(file_data) > 50_000_000: # 50MB
        return web.json_response(
            {"error": True, "message": "File too large. Max is 50MB."}, status=413
        )

    image = await Image.create(
        filename, uuid4().hex, session["user_id"], file_data, image_db
    )

    return web.json_response(
        {"error": False, "message": "Image uploaded.", "image": image.dict()}
    )


@routes.get("/images/{image_id}")
async def get_image(request: web.Request) -> web.Response:
    image_id = request.match_info["image_id"]
    image = await image_db.find_one({"id": image_id})

    if not image:
        return web.json_response(
            {"error": True, "message": "Image not found."}, status=404
        )

    return web.Response(text=BASE_HTML_TEMPLATE.format(image))


@routes.delete("/images/{image_id}")
async def delete_image(request: web.Request) -> web.Response:
    token = request.headers.get("Authorization")
    if not token:
        return web.json_response(
            {"error": True, "message": "No token provided."}, status=401
        )

    session = await sessions.find_one({"token": token})

    if not session:
        return web.json_response(
            {"error": True, "message": "Invalid token."}, status=403
        )

    user = await auth_db.find_one({"id": session["user_id"]})

    image_id = request.match_info["image_id"]
    image = await image_db.find_one({"id": image_id})

    if not image:
        return web.json_response(
            {"error": True, "message": "Image not found."}, status=404
        )

    if image["user_id"] != session["user_id"] and not user["admin"]:
        return web.json_response(
            {"error": True, "message": "You cannot delete this image."}, status=403
        )

    await image_db.delete_one(image)

    return web.json_response({"error": False, "message": "Image deleted."})


app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, port=config["port"])

from dataclasses import dataclass
from uuid import uuid4


@dataclass
class User:
    id: str
    username: str
    _username: str  # Lower
    email: str
    password: str
    images: list[str]  # List of IDs
    admin: bool

    @classmethod
    async def create(
        cls, username: str, email: str, password: str, auth_db, admin=False
    ):
        payload = {
            "username": username,
            "_username": username.lower(),
            "email": email,
            "password": password,
            "images": [],
            "id": uuid4().hex,
            "admin": admin,
        }
        await auth_db.insert_one(payload)
        return cls(**payload)

    async def delete(self, auth_db):
        await auth_db.delete_one({"id": self.id})

    async def update(self, auth_db):
        await auth_db.update_one({"id": self.id}, {"$set": self.dict()})

    async def add_image(self, image_id: str, auth_db):
        self.images.append(image_id)
        await self.update(auth_db)

    async def remove_image(self, image_id: str, auth_db):
        self.images.remove(image_id)
        await self.update(auth_db)


@dataclass
class Image:
    id: str
    name: str
    description: str
    url: str
    owner_id: str  # User
    contents: bytes

    @classmethod
    async def create(
        cls,
        name: str,
        description: str,
        url: str,
        owner_id: str,
        contents: bytes,
        image_db,
    ):
        payload = {
            "name": name,
            "description": description,
            "url": url,
            "owner_id": owner_id,
            "contents": contents,
            "id": uuid4().hex,
        }
        await image_db.insert_one(payload)
        return cls(**payload)

    async def delete(self, image_db):
        await image_db.delete_one({"id": self.id})

    async def update(self, image_db):
        await image_db.update_one({"id": self.id}, {"$set": self.dict()})


__all__ = ["User", "Image"]

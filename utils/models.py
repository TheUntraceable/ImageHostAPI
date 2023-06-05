from dataclasses import dataclass
from uuid import uuid4

from argon2 import PasswordHasher


@dataclass
class User:
    id: str
    username: str
    _username: str  # Lower
    email: str
    _email: str  # Lower
    password: str
    images: list[str]  # List of IDs
    admin: bool
    quota: int = 1000  # MB

    @classmethod
    async def create(
        cls,
        username: str,
        email: str,
        password: str,
        auth_db,
        admin=False,
        quota=1000,
        password_hasher: PasswordHasher = PasswordHasher,
    ):
        payload = {
            "username": username,
            "_username": username.lower(),
            "email": email,
            "_email": email.lower(),
            "password": password_hasher.hash(password),
            "images": [],
            "id": uuid4().hex,
            "admin": admin,
            "quota": quota,  # MB
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

    def dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "images": self.images,
            "id": self.id,
            "quota": self.quota,
        }


@dataclass
class Image:
    id: str
    name: str
    url: str
    owner_id: str  # User
    contents: bytes

    @classmethod
    async def create(
        cls,
        name: str,
        url: str,
        owner_id: str,
        contents: bytes,
        image_db,
    ):
        payload = {
            "name": name,
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

    def dict(self):
        return {
            "name": self.name,
            "url": self.url,
            "owner_id": self.owner_id,
            "contents": self.contents,
            "id": self.id,
        }


__all__ = ["User", "Image"]

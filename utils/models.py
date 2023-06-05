from dataclasses import dataclass


@dataclass
class User:
    id: str
    username: str
    _username: str  # Lower
    email: str
    password: str
    images: list[str]  # List of IDs


@dataclass
class Image:
    id: str
    name: str
    description: str
    url: str
    owner_id: str  # User
    contents: bytes


__all__ = ["User", "Image"]

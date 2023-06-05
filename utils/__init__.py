from aiohttp import web

from .setup_logger import configure_logger
from .models import User, Image

BASE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
        <style>
            body {
                background-color: #131B23;
            }
            .image {
                width: 100vw;
                height: 100vh;
                background-image: url("{image.url}");
                background-size: cover;
                background-position: center;
            }
        </style>
        <meta content="{image.name}" property="og:title" />
        <meta content="#2F3136" data-react-helmet="true" name="theme-color" />
        <meta name="twitter:card" content="{image.contents}">
    </head>
</html>
"""

ADMIN_USER_DISPLAY_FORMAT = """
Username: {user.username}
Email: {user.email}
Password: {password}
"""


@web.middleware
async def logging_middleware(
    request: web.Request, handler: web.RequestHandler
) -> web.Response:
    response = await handler(request)
    request.app.logger.debug(f"%t {request.method} {request.path} {response.status}")
    return response


__all__ = [
    "configure_logger",
    "User",
    "Image",
    "BASE_HTML_TEMPLATE",
    "ADMIN_USER_DISPLAY_FORMAT",
    "logging_middleware",
]

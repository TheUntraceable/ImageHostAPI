from logging import getLogger
from json import load
from os import listdir

from aiohttp import web

from .utils import configure_logger

with open("config.json", "r") as f:
    config = load(f)

logger = getLogger(__name__)
configure_logger(logger)

app = web.Application(logger=logger)

for possible_route in listdir("routes"):
    if possible_route.endswith(".py"):
        exec(
            f"from routes.{possible_route[:-3]} import routes as {possible_route[:-3]}"
        )
        exec(f"app.add_routes({possible_route[:-3]})")


if __name__ == "__main__":
    web.run_app(app, port=config["port"])

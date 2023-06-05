from time import time
from logging import Logger, Formatter, FileHandler


def configure_logger(logger: Logger):
    logger.setLevel(-100)
    handler = FileHandler(filename=f"./logs/{time()}", encoding="utf-8", mode="w")
    handler.setFormatter(
        Formatter(
            fmt="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
            datefmt="%d/%m/%Y %H:%M:%S",
        )
    )
    logger.addHandler(handler)


__all__ = ["configure_logger"]

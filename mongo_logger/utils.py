import json
import logging

import pymongo

pymongo_version = int(pymongo.version.split(".")[0])
if pymongo_version >= 3:
    from pymongo.collection import ReturnDocument  # noqa: F401

from .exceptions import LogConfigError

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Only imports the below statements during type checking

    from .handlers import BaseMongoLogHandler

console = logging.getLogger('mongolog-int')


def get_mongolog_handler(logger_name=None, show_logger_names=False):
    """
    Return the first MongoLogHandler found in the list of defined loggers.
    NOTE: If more than one is defined, only the first one is used.
    """

    if logger_name:
        logger_names = [logger_name]
    else:
        logger_names = [''] + list(logging.Logger.manager.loggerDict)

    if show_logger_names:
        console.info(
            "get_mongolog_handler(): Logger_names: %s",
            json.dumps(logger_names, indent=4, sort_keys=True, default=str)
        )

    for name in logger_names:
        logger = logging.getLogger(name)
        handler = None
        for _handler in logger.handlers:
            if isinstance(_handler, BaseMongoLogHandler):
                handler = _handler
                break
        if handler:
            console.debug("found handler: %s", handler)
            break

    if not handler:
        if logger_name:
            raise LogConfigError(
                "logger '%s' does not have a mongolog based handler associated with it."
                % logger_name
            )

        raise LogConfigError("There are no loggers with a mongolog based handler. "
                             "Please see documentation about setting up LOGGING.")
    return handler


class LogRecord(dict):
    pass

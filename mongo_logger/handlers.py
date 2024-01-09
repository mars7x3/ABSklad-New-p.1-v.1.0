from __future__ import print_function
import logging
from logging import Handler, NOTSET
from datetime import datetime as dt

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

import traceback
import json
import uuid

import pymongo

from pymongo.collection import ReturnDocument

from .utils import LogRecord
from .exceptions import MissingConnectionError

logger = logging.getLogger('')


class BaseMongoLogHandler(Handler):
    REFERENCE = 'reference'
    EMBEDDED = 'embedded'

    def __init__(self, level=NOTSET, connection=None, database='mongolog', collection='mongolog',
                 verbose=None, time_zone="local", record_type="embedded", max_keep=100,
                 *args, **kwargs) -> None:
        super().__init__(level)
        self.connection = connection
        self.database = database
        self.collection = collection

        valid_record_types = [self.REFERENCE, self.EMBEDDED]

        if record_type not in valid_record_types:
            raise ValueError("record_type myst be one of %s" % valid_record_types)

        if not self.connection:
            raise MissingConnectionError("Missing 'connection' key")

        # the type of document we store
        self.record_type = record_type

        # number of dates to keep in embedded document
        self.max_keep = max_keep

        # used to determine which time setting is used in the simple record_type
        self.time_zone = time_zone

        # if True will print each log_record to console before writing to mongo
        self.verbose = verbose

        self.client = pymongo.MongoClient(self.connection, serverSelectionTimeoutMS=5)
        self.db = self.client[self.database]
        self.collection = self.db[self.collection]
        self.timestamp = self.db.timestamp

    def __str__(self):
        return self.connection

    def get_db(self):
        """ Return a handler to the database handler """
        return getattr(self, "db", None)

    def get_timestamp_collection(self):
        return getattr(self, "timestamp", None)

    def get_collection(self):
        """ Return the collection being used by MongoLogHandler """
        return getattr(self, "mongolog", None)

    def check_keys(self, record):
        """ Check for . and $ in two levels of keys below msg. """
        if not isinstance(record['msg'], dict):
            return record

        for k, v in list(record['msg'].items()):
            self._check_keys(k, v, record['msg'])

        return record

    def _check_keys(self, k, v, _dict):
        """ Recursively check key's for special characters. """

        _dict[self.new_key(k)] = _dict.pop(k)

        if isinstance(v, dict):
            for nk, vk in list(v.items()):
                self._check_keys(nk, vk, v)

        # We could also have an array of dictionaries so we check those as well.
        if isinstance(v, list):
            for l in v:
                if isinstance(l, dict):
                    for nk, vk in list(l.items()):
                        self._check_keys(nk, vk, l)

    @staticmethod
    def new_key(key):
        if key[0] == "$":
            key = u"＄" + key[1:]
        return key

    def create_log_record(self, record):
        """
        Convert the python LogRecord to a MongoLog Record.
        Also add a UUID which is a combination of the log message and log level.

        Override in subclasses to change log record formatting.
        See SimpleMongoLogHandler and VerboseMongoLogHandler
        """
        # This is still a python LogRecord Object that we are manipulating
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info)

        record = LogRecord(json.loads(json.dumps(record.__dict__, default=str)))
        if "mongolog.management.commands" in record['name']:
            return {'uuid': 'none', 'time': 'none', 'level': 'MONGOLOG-INTERNAL'}
        record = self.check_keys(record)

        record.update({
            'uuid': uuid.uuid4().hex,
            'time': dt.utcnow() if self.time_zone == 'utc' else dt.now(),
        })

        # If we are using an embedded document type
        # we need to create the dates array
        if self.record_type == self.EMBEDDED:
            record['dates'] = [record['time']]

        return record

    def formatException(self, ei):
        """
        Format and return the specified exception information as a string.

        This default implementation just uses
        traceback.print_exception()
        """
        sio = StringIO()

        traceback.print_exception(ei[0], ei[1], ei[2], None, sio)
        s = sio.getvalue()
        sio.close()
        if s[-1:] == "\n":
            s = s[:-1]
        return s

    def emit(self, record):
        """
        From python:  type(record) == LogRecord
        https://github.com/certik/python-2.7/blob/master/Lib/logging/__init__.py#L230
        """
        log_record = self.create_log_record(record)

        log_record.get('uuid', ValueError("You must have a uuid in your LogRecord"))

        if self.verbose:
            print(json.dumps(log_record, sort_keys=True, indent=4, default=str))

        if self.record_type == self.EMBEDDED:
            self.insert_embedded(log_record)

        elif self.record_type == self.REFERENCE:
            self.reference_log_pymongo(log_record)

    def insert_embedded(self, log_record):
        """
        Insert an embedded document.  Embedded documents have a 'counter'
        variable that increments each time the document is seen.  The 'date'
        array is capped at the last 'max_keep'
        """
        log_record['created'] = log_record.pop('time')
        self.collection.insert_one(log_record)

    def reference_log_pymongo(self, log_record):
        query = {'uuid': log_record['uuid']}
        self.collection.find_one_and_replace(
            query,
            log_record,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        self.timestamp.insert({'uuid': log_record['uuid'], 'ts': log_record['time']})


class CustomMongoLogHandler(BaseMongoLogHandler):
    def create_log_record(self, record):
        record = super().create_log_record(record)
        status_code = record.get('status_code')
        request = record.get('request')
        server_time = record.get('server_time')
        args = record['args']
        msg = record['msg']

        if not isinstance(msg, dict) and isinstance(args, dict):
            msg = record['msg'] % args
        elif not isinstance(msg, dict) and not isinstance(args, dict):
            msg = record['msg'] % tuple(args)

        log = {
            'level': record['levelname'],
            'msg': msg,
            'name': record['name'],
            'status_code': status_code,
            'module_info': {
                'module_name': record['module'],
                'module_path': record['pathname'],
                'file_name': record['filename'],
                'func_name': record['funcName'],
                'script_line': record['lineno']
            },
            'process_info': {
                'process_name': record['processName'],
                'process_number': record['process']
            },
            'thread_info': {
                'thread_name': record['threadName'],
                'thread_number': record['thread']
            },
            'server_time': server_time,
            'request': request,
            'uuid': record['uuid'],
            'time': record['time'],
            'exc_info': record['exc_info'],
            'exc_text': record['exc_text'],
            'created': record['created']
        }

        return log

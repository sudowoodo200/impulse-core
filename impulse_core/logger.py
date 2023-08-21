import json, os, sys, time, uuid
import queue
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Protocol, cast
from enum import Enum
import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
import functools as ft, hashlib
import pymongo as pm

END_OF_STREAM_TAG = None
@dataclass
class BaseAsyncLogger:
    uri: str
    num_threads: int = 4
    _session_client: Any = None
    _pool: ThreadPoolExecutor = field(init = False)
    _EOS_Tag: Any = END_OF_STREAM_TAG

    def __post_init__(self):
        assert self.uri is not None, "Target URI must be specified."
        self._pool = ThreadPoolExecutor(max_workers=self.num_threads)
    
    def auth(self, *args, **kwargs) -> bool: 
        return True

    def log(self, 
            payload: Union[str, Dict[str, Any], asyncio.Queue], 
            metadata: Optional[Dict[str, Any]] = None, 
            *args, **kwargs) -> None:
        """
        Write data to target URI as a JSON.
        payload: Dict[str, Any]    - the data to be written
        metadata: Dict[str, Any]   - the optional metadata to be written
        """

        if isinstance(payload, queue.Queue):
            payload = cast(queue.Queue, payload)
            self._pool.submit(self._write_stream, payload, metadata, *args, **kwargs)
        else:
            payload = cast(Union[str, Dict[str, Any]], payload)
            self._pool.submit(self._write, payload, metadata, *args, **kwargs)
    
    def _write(self, 
               payload: Union[str, Dict[str, Any]], 
               metadata: Optional[Dict[str, Any]], 
               *args, **kwargs) -> Any: ...

    def _write_stream(self, 
                      payload: queue.Queue, 
                      metadata: Optional[Dict[str, Any]], 
                      *args, **kwargs) -> None:
        """
        Write data to target URI as a JSON.
        data_stream: asyncio.Queue  - the data stream to be written
        metadata: Dict[str, Any]    - the metadata to be written
        """

        def read_stream(input: queue.Queue):
            buffer = ""
            while True:
                data = input.get()
                if data == self._EOS_Tag:
                    break
                buffer += data
            return buffer

        buffer = read_stream(payload)
        self._write(buffer, metadata, *args, **kwargs)

    def shutdown(self, 
                 wait: bool = True, 
                 cancel_futures: bool = False, 
                 *args, **kwargs) -> None:
        """
        Shutdown the logger.
        wait: bool              - whether to wait for all threads to finish
        cancel_futures: bool    - whether to cancel all pending futures
        """
        self._pool.shutdown(wait, cancel_futures = cancel_futures, *args, **kwargs)

LOCAL_ENTRY_SEP ="\n\n"
@dataclass
class LocalLogger(BaseAsyncLogger):
    uri: str = "./.impulselogs/"
    filename: str = "log_{timestamp}.json"
    entry_sep: str = LOCAL_ENTRY_SEP
    num_threads: int = 1 # dumb way to ensure no file contention

    def __post_init__(self):
        super().__post_init__()
        self.filename = self.filename.format(
            timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        )
        if not os.path.exists(self.uri):
            os.makedirs(self.uri)
        self.filename = os.path.join(self.uri, self.filename)

    def _write(self, 
               payload: Union[str,Dict[str, Any]], 
               metadata: Optional[Dict[str, Any]] = None,
               *args, **kwargs):

        data = json.dumps({
                    "payload": payload,
                    "log_metadata": metadata,
                }, indent = 4)

        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                f.write(data)
        else:
            with open(self.filename, "a+") as f:
                f.write(self.entry_sep)
                f.write(data)


@dataclass
class MongoLogger(BaseAsyncLogger):

    uri: str = "mongodb://root:example@localhost:27017/"
    db_name: str = "impulse_logs"
    collection_name: str = "logs"

    def __post_init__(self):
        super().__post_init__()
        self._session_client = pm.MongoClient(self.uri)
        self._db = self._session_client[self.db_name]
        self._collection = self._db[self.collection_name]
    
    def auth(self, credentials: Any) -> bool:
        """
        Authenticate with MongoDB.
        user: str       - the username
        password: str   - the password
        """
        
        if self.auth_type == "userpass":
            try:
                self.uri = self.uri.format(**credentials)
                self._session_client = pm.MongoClient(self.uri)
                return True
            except Exception as e:
                raise e
        else:
            raise Exception("Auth type not supported")
    
    def _write(self, 
               payload: Union[str, Dict[str, Any]], 
               metadata: Optional[Dict[str, Any]],
               *args, **kwargs):
        
        data = {
            "payload": payload,
            "log_metadata": metadata,
        }

        self._collection.insert_one(data)


@dataclass
class DummyLogger(BaseAsyncLogger):
    uri: str = ""
    io_time: float = 0.1
    buffer: List[Dict[str, Any]] = field(default_factory = list)

    def __post_init__(self):
        super().__post_init__()

    def _write(self, 
               payload: Union[str,Dict[str, Any]], 
               metadata: Optional[Dict[str, Any]] = None,
               *args, **kwargs):

        time.sleep(self.io_time)
        self.buffer.append({
            "payload": payload,
            "log_metadata": metadata,
        })

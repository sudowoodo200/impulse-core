import json, os, sys, time, uuid
import queue
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Protocol, cast
from enum import Enum
import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
import functools as ft, hashlib

## Base Class #################################################################
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

LOCAL_ENTRY_SEP ="\n"
@dataclass
class LocalLogger(BaseAsyncLogger):
    uri: str = "./.impulse_logs/"
    filename: str = "logs_{timestamp}.json"
    entry_sep: str = LOCAL_ENTRY_SEP
    num_threads: int = 1 # dumb way to ensure no file contention

    def __post_init__(self):
        super().__post_init__()
        self.filename = self.filename.format(
            timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        )
        self.filename = os.path.join(self.uri, self.filename)
        if not os.path.exists(self.uri):
            os.makedirs(self.uri)
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                f.write("")

    def _write(self, 
               payload: Union[str,Dict[str, Any]], 
               metadata: Optional[Dict[str, Any]] = None,
               *args, **kwargs):

        data = {
            "payload": payload,
            "log_metadata": metadata,
        }
        with open(self.filename, "a+") as f:
            f.write(self.entry_sep + json.dumps(data))
    
    def log(self, 
            payload: Union[str, Dict[str, Any], asyncio.Queue], 
            metadata: Optional[Dict[str, Any]] = None, 
            *args, **kwargs) -> None:
        """
        Write a file to a directory as a JSON.
        payload: Dict[str, Any]    - the data to be written
        metadata: Dict[str, Any]   - the metadata to be written
        request_id: str            - the request ID; all logs with the same request ID will be written to the same file
        tag: str                   - a tag to be appended to the filename
        """
        super().log(payload, metadata = metadata)


import pymongo as pm
DEFAULT_CREDENTIALS = {
    "user": "root",
    "password": "example"
}

@dataclass
class MongoLogger(BaseAsyncLogger):

    uri: str = "mongodb://{user}:{password}@localhost:27017/"
    auth_type: str = "userpass"
    credentials: str = field(default_factory=dict)
    db_name: str = "impulse_logs"
    collection_name: str = "logs"

    def __post_init__(self):
        super().__post_init__()
        self.credentials = DEFAULT_CREDENTIALS
        if self.auth(self.credentials):
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
                return False
        
        else:
            return False
    
    def _write(self, 
               payload: Union[str, Dict[str, Any]], 
               metadata: Optional[Dict[str, Any]],
               *args, **kwargs):
        
        data = {
            "payload": payload,
            "log_metadata": metadata,
        }

        self._collection.insert_one(data)


## Dev ###############################################################

## Unit Tests
def main():

    logger = MongoLogger()

    print(f"{datetime.now().strftime('%H:%M:%S')} Logging...")
    logger.log(payload={"test": "test"}, metadata={"user": "testuser"}, logid="test")
    logger.log(payload="another test", metadata={"user": "testuser"}, logid="test")
    print(f"{datetime.now().strftime('%H:%M:%S')} Next...")

    async def stream_in( log_stream: queue.Queue, name = "1"):

        log_stream.put(f"Stream {name}: ")
        for i in range(4):
            await asyncio.sleep(0.5)
            print(f"{datetime.now().strftime('%H:%M:%S')} Stream {name} at Token {i}...")
            log_stream.put_nowait(f"Token {i}. ")
            print(f"{datetime.now().strftime('%H:%M:%S')} Stream {name} has log_stream of size {log_stream.qsize()}...")

        log_stream.put(END_OF_STREAM_TAG)
        print(f"{datetime.now().strftime('%H:%M:%S')} Stream {name} finished.")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    buffering_queue_1 = queue.Queue()
    logger.log(buffering_queue_1, metadata={"user": "teststream"}, logfile="test")

    buffering_queue_2 = queue.Queue()
    logger.log(buffering_queue_2, metadata={"user": "teststream"}, logfile="test")

    task_1 = loop.create_task(stream_in(buffering_queue_1, name = "1"))
    print(f"{datetime.now().strftime('%H:%M:%S')} Streaming task 1 started.")

    task_2 = loop.create_task(stream_in(buffering_queue_2, name = "2"))
    print(f"{datetime.now().strftime('%H:%M:%S')} Streaming task 2 started.")

    loop.run_until_complete(asyncio.gather(task_1, task_2))
    logger.shutdown()

if __name__ == "__main__":
    main()
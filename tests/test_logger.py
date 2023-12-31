import asyncio
import queue
import pytest
import os
import json
from pathlib import Path
from impulse_core.logger import BaseAsyncLogger, LocalLogger, LOCAL_ENTRY_SEP, END_OF_STREAM_TAG

# Fixture setups
@pytest.fixture
def testdir():
    return Path("./tests/")

@pytest.fixture
def local_logger(testdir):

    sub_dir = testdir / "temp"
    if not os.path.exists(sub_dir):
        sub_dir.mkdir()
    assert os.path.exists(sub_dir)
    
    yield LocalLogger(uri=str(sub_dir))

    for item in sub_dir.iterdir():
        item.unlink()  # Removes files
    
    sub_dir.rmdir()   # Removes the directory itself

# Tests for LocalLogger
def test_local_logger_init(local_logger):
    assert local_logger._pool._max_workers == 1

def test_local_logger_log_to_file(local_logger):
    payload = {"key": "value"}
    metadata = {"meta": "data"}

    local_logger.log(payload, metadata=metadata)
    local_logger.shutdown()
    
    filepath = Path(local_logger.filename)
    assert filepath.exists(), f"File {filepath} does not exist."

    with open(filepath, 'r') as f:
        content = f.read()
        logged_data = json.loads(content)
        
        assert logged_data["payload"] == payload , f"Payload {logged_data['payload']} does not match {payload}"
        assert logged_data["log_metadata"] == metadata , f"Metadata {logged_data['log_metadata']} does not match {metadata}"

    os.remove(filepath)

def test_local_logger_stream(local_logger):

    async def stream_in( log_stream: queue.Queue, name: str = "1"):

        log_stream.put(f"Stream {name}: ")
        for i in range(4):
            log_stream.put_nowait(f"Token {i}. ")

        log_stream.put(END_OF_STREAM_TAG)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    buffering_queue = queue.Queue()
    metadata = {"user": "teststream"}
    local_logger.log(buffering_queue, metadata=metadata)

    task = loop.create_task(stream_in(buffering_queue, name = "1"))
    loop.run_until_complete(task)

    local_logger.shutdown() ## this is necessary to wait for the thread to finish
    
    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)
        logged_data = json.loads(content[0])
        
        assert logged_data["payload"] == "Stream 1: Token 0. Token 1. Token 2. Token 3. "
        assert logged_data["log_metadata"] == metadata

    os.remove(filepath)
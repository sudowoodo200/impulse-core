import asyncio
from dataclasses import dataclass
import queue
from typing import AsyncGenerator
from datetime import datetime as dt
import pytest
import os
import json
from pathlib import Path
from impulse_trace.tracer import ImpulseTracer
from impulse_trace.logger import LocalLogger

## ROADMAP ####################################################################
# TODO: Write tests for stack trace logging
# TODO: Write tests for trace logging

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

    print(str(sub_dir))
    
    yield LocalLogger(uri=str(sub_dir))

    for item in sub_dir.iterdir():
        item.unlink()  # Removes files
    
    sub_dir.rmdir()   # Removes the directory itself

@pytest.fixture
def tracer_metadata():
    return {"tracing_context": "unit_test"}

@pytest.fixture
def tracer(local_logger, tracer_metadata):
    return ImpulseTracer(local_logger, tracer_metadata)

# Basic functions
def test_tracer_function(tracer, tracer_metadata):

    local_logger = tracer.logger
    log_target = "test"
    thread_name = "test_fn"

    @tracer.hook(thread_name = thread_name, log_target=log_target)
    def test_fn(x: int, y: int, n: int) -> str:
        return str(x + n * y)
    
    x = 1
    y = 2
    n = 5
    payload = test_fn(x, y, n=n)
    tracer.shutdown()

    assert log_target in local_logger.log_targets
    filepath = Path(local_logger.uri) / local_logger.log_targets[log_target]
    
    assert filepath.exists()
    with open(filepath, 'r') as f:
        content = f.read()
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "trace_thread": thread_name,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_function.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "args": {
                "x": x,
                "y": y,
            },
            "kwargs": {
                "n": n
            }
        }
        assert logged_data["log_metadata"] is None
        assert logged_data["log_target"] == log_target

    os.remove(filepath)

# Basic Methods
def test_tracer_method(tracer, tracer_metadata):

    local_logger = tracer.logger
    log_target = "test"
    thread_name = "test_method"

    @dataclass
    class TestClass:
        x: int
        y: int

        @tracer.hook(thread_name, log_target=log_target)
        def test_fn(self, n: int) -> str:
            return str(self.x + self.y *n)
    
    x = 1
    y = 2
    n = 5
    test_instance = TestClass(x = x, y = y)
    payload = test_instance.test_fn(n)
    tracer.shutdown()

    assert log_target in local_logger.log_targets
    filepath = Path(local_logger.uri) / local_logger.log_targets[log_target]
    
    assert filepath.exists()
    with open(filepath, 'r') as f:
        content = f.read()
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "trace_thread": thread_name,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_method.<locals>.TestClass.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["self", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "args": {
                "self": str(test_instance),
                "n": n,
            },
            "kwargs": {},
            "instance_attr": {
                "x": x,
                "y": y
            }
        }
        assert logged_data["log_metadata"] is None
        assert logged_data["log_target"] == log_target

    os.remove(filepath)

# Basic coroutines
def test_tracer_coroutine(tracer, tracer_metadata):

    local_logger = tracer.logger
    log_target = "test"
    thread_name = "test_coro"

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    @tracer.hook(thread_name, log_target=log_target)
    async def test_fn(x: int, y: int, n: int) -> str:
        return str(x + n * y)
    
    x = 1
    y = 2
    n = 5
    payload = loop.run_until_complete(test_fn(x, y, n=n))
    tracer.shutdown()
    loop.close()

    assert log_target in local_logger.log_targets
    filepath = Path(local_logger.uri) / local_logger.log_targets[log_target]
    
    assert filepath.exists()
    with open(filepath, 'r') as f:
        content = f.read()
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "trace_thread": thread_name,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_coroutine.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Coroutine"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "args": {
                "x": x,
                "y": y,
            },
            "kwargs": {
                "n": n
            }
        }
        assert logged_data["log_metadata"] is None
        assert logged_data["log_target"] == log_target

    os.remove(filepath)

# Basic async generators
def test_tracer_agen(tracer, tracer_metadata):

    local_logger = tracer.logger
    log_target = "test"
    thread_name = "test_agen"

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    @tracer.hook(thread_name, log_target=log_target)
    async def test_fn(x: int, y: int, n: int) -> AsyncGenerator[str, None]:
        for i in range(n):
            yield str(x + i * y)

    async def run_test_fn(fn: AsyncGenerator[str, None], x: int, y: int, n: int):
        output = ""
        async for i in fn(x,y,n=n):
            output += i
        return output

    x = 1
    y = 2
    n = 5
    payload = loop.run_until_complete(run_test_fn(test_fn, x, y, n=n))
    tracer.shutdown()
    loop.close()

    assert log_target in local_logger.log_targets
    filepath = Path(local_logger.uri) / local_logger.log_targets[log_target]
    
    assert filepath.exists()
    with open(filepath, 'r') as f:
        content = f.read()
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "trace_thread": thread_name,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_agen.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "AsyncGenerator"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "args": {
                "x": x,
                "y": y,
            },
            "kwargs": {
                "n": n
            }
        }
        assert logged_data["log_metadata"] is None
        assert logged_data["log_target"] == log_target

    os.remove(filepath)

# Exceptions
def test_tracer_exception(tracer, tracer_metadata):

    local_logger = tracer.logger
    log_target = "test"
    thread_name = "test_fn_exception"
    hook_name = "test_hook"
    exception_message = "Error"

    @tracer.hook(thread_name, log_target=log_target)
    def test_fn(x: int, y: int, n: int) -> str:
        raise Exception(exception_message)
    
    x = 1
    y = 2
    n = 5
    try:
        payload = test_fn(x, y, n=n)
    except:
        pass
    tracer.shutdown()

    assert log_target in local_logger.log_targets
    filepath = Path(local_logger.uri) / local_logger.log_targets[log_target]
    
    assert filepath.exists()
    with open(filepath, 'r') as f:
        content = f.read()
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "trace_thread": thread_name,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_exception.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == None
        assert logged_data["payload"]["exception"] == exception_message
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "args": {
                "x": x,
                "y": y,
            },
            "kwargs": {
                "n": n
            }
        }
        assert logged_data["log_metadata"] is None
        assert logged_data["log_target"] == log_target

    os.remove(filepath)
import asyncio
from dataclasses import dataclass
import queue
from typing import AsyncGenerator, Generator
from datetime import datetime as dt
import pytest
import os
import json
from pathlib import Path
from impulse_core.tracer import ImpulseTracer
from impulse_core.logger import LOCAL_ENTRY_SEP, LocalLogger

## ROADMAP ####################################################################

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

@pytest.fixture
def tracer_metadata():
    return {"tracing_context": "unit_test"}

@pytest.fixture
def tracer(local_logger, tracer_metadata):
    return ImpulseTracer(local_logger, tracer_metadata)

# Basic functions
def test_tracer_function(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_fn"

    @tracer.hook(thread_id = thread_id)
    def test_fn(x: int, y: int, n: int) -> str:
        return str(x + n * y)
    
    x = 1
    y = 2
    n = 5
    payload = test_fn(x, y, n=n)
    tracer.shutdown()

    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)[0]
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_function.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "x": x,
            "y": y,
            "n": n
        }
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}

    os.remove(filepath)

# Basic Methods
def test_tracer_method(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_method"

    @dataclass
    class TestClass:
        x: int
        y: int

        @tracer.hook(thread_id)
        def test_fn(self, n: int) -> str:
            return str(self.x + self.y *n)
    
    x = 1
    y = 2
    n = 5
    test_instance = TestClass(x = x, y = y)
    payload = test_instance.test_fn(n)
    tracer.shutdown()

    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)[0]
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_method.<locals>.TestClass.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["self", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "self": {
                "type": "instance",
                "classname": TestClass.__name__,
                "attr": {
                    "x": x,
                    "y": y
                }
            },
            "n": n
        }
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}

    os.remove(filepath)

# Class Wrappers
def test_tracer_class(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_class"

    @tracer.class_hook(thread_id, attr_names = ["test_fn"])
    class TestClass:
        x: int
        y: int

        def __init__(self, x: int = 1, y: int = 2):
            self.x = x
            self.y = y

        def test_fn(self, n: int) -> str:
            return str(self.x + self.y *n)
    
    x = 1
    y = 2
    n = 5
    test_instance = TestClass(x = x, y = y)
    payload = test_instance.test_fn(n)
    tracer.shutdown()

    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)[0]
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_class.<locals>.TestClass.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["self", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "self": {
                "type": "instance",
                "classname": TestClass.__name__,
                "attr": {
                    "x": x,
                    "y": y
                }
            },
            "n": n
        }
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}

    os.remove(filepath)


# Basic coroutines
def test_tracer_coroutine(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_coro"

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    local_logger = tracer.logger
    thread_id = "test_fn"

    @tracer.hook(thread_id = thread_id)
    async def test_fn(x: int, y: int, n: int) -> str:
        return str(x + n * y)
    
    x = 1
    y = 2
    n = 5
    payload = loop.run_until_complete(test_fn(x, y, n=n))
    tracer.shutdown()
    loop.close()

    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)[0]
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_coroutine.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Coroutine"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "x": x,
            "y": y,
            "n": n
        }
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}

    os.remove(filepath)

# # Basic async generators
def test_tracer_agen(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_agen"

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    @tracer.hook(thread_id)
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

    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)[0]
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_agen.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "AsyncGenerator"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "x": x,
            "y": y,
            "n": n
        }
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}

    os.remove(filepath)

## Synchrnous Generator Tracing
def test_tracer_gen(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_gen"

    @tracer.hook(thread_id)
    def test_fn(x: int, y: int, n: int) -> Generator[str, None, None]:
        for i in range(n):
            yield str(x + i * y)

    def run_test_fn(fn: Generator[str, None, None], x: int, y: int, n: int):
        output = ""
        for i in fn(x,y,n=n):
            output += i
        return output

    x = 1
    y = 2
    n = 5
    payload = run_test_fn(test_fn, x, y, n=n)

    filepath = Path(local_logger.filename)
    tracer.shutdown()
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)[0]
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_gen.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Generator"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "x": x,
            "y": y,
            "n": n
        }
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}

    os.remove(filepath)


# Basic exceptions
def test_tracer_exception(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_fn"
    exception_msg = "Test Exception"

    @tracer.hook(thread_id = thread_id)
    def test_fn(x: int, y: int, n: int) -> str:
        raise Exception(exception_msg)
    
    x = 1
    y = 2
    n = 5
    try:
        payload = test_fn(x, y, n=n)
    except Exception as e:
        pass
    tracer.shutdown()

    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)[0]
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_exception.<locals>.test_fn"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["status"] == "error"
        assert logged_data["payload"]["exception"] == exception_msg
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "x": x,
            "y": y,
            "n": n
        }
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}

    os.remove(filepath)

# Stack trace
def test_tracer_stack_trace(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_fn"

    @tracer.hook(thread_id = thread_id)
    def test_fn(x: int, y: int, n: int) -> str:
        return str(x + n * y)
    
    def test_fn_1(x: int, y: int, n: int) -> str:
        return test_fn(x, y, n=n)

    @tracer.hook(thread_id = thread_id)
    def test_fn_2(x: int, y: int, n: int) -> str:
        return test_fn_1(x, y, n=n)

    x = 1
    y = 2
    n = 5
    payload = test_fn_2(x, y, n=n)
    tracer.shutdown()

    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)[1]
        logged_data = json.loads(content)
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_stack_trace.<locals>.test_fn_2"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data["payload"]["output"] == payload
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "x": x,
            "y": y,
            "n": n
        }
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}
        assert len(logged_data["payload"]["stack_trace"]["parents"]) == 1
        assert len(logged_data["payload"]["stack_trace"]["children"]) == 1
        assert logged_data["payload"]["stack_trace"]["parents"][0]["fn_name"] == "<module>"
        assert logged_data["payload"]["stack_trace"]["children"][0]["fn_name"] == "test_tracer_stack_trace.<locals>.test_fn"

    os.remove(filepath)

# Stack trace with exceptions
def test_tracer_stack_trace_exception(tracer, tracer_metadata):

    local_logger = tracer.logger
    thread_id = "test_fn"
    exception_msg = "Test Exception"

    @tracer.hook(thread_id = thread_id)
    def test_fn(x: int, y: int, n: int) -> str:
        return str(x + n * y)
    
    def test_fn_1(x: int, y: int, n: int) -> str:
        raise Exception("Test Exception")

    @tracer.hook(thread_id = thread_id)
    def test_fn_2(x: int, y: int, n: int) -> str:
        return test_fn_1(x, y, n=n)

    x = 1
    y = 2
    n = 5

    try:
        payload = test_fn_2(x, y, n=n)
    except:
        pass

    payload_2 = test_fn(x, y, n=n)
    tracer.shutdown()

    filepath = Path(local_logger.filename)
    assert filepath.exists()

    with open(filepath, 'r') as f:
        content = f.read().split(LOCAL_ENTRY_SEP)
        logged_data = json.loads(content[0])
        logged_data_2 = json.loads(content[1])
        
        assert set({
            "tracer_id": tracer.instance_id,
            "thread_id": thread_id,
            "tracer_metadata": tracer_metadata
        }).issubset(set(logged_data["payload"]["trace_module"]))
        assert logged_data["payload"]["function"]["name"] == "test_tracer_stack_trace_exception.<locals>.test_fn_2"
        assert logged_data["payload"]["function"]["type"] == "Function"
        assert logged_data["payload"]["function"]["args"] == ["x", "y", "n"]
        assert type(logged_data["payload"]["call_id"]) == str
        assert logged_data["payload"]["arguments"] == {
            "x": x,
            "y": y,
            "n": n
        }
        assert logged_data["payload"]["status"] == "error"
        assert logged_data["payload"]["exception"] == exception_msg
        assert logged_data["log_metadata"] == {"source": "impulse_tracer"}
        assert len(logged_data["payload"]["stack_trace"]["parents"]) == 1
        assert len(logged_data["payload"]["stack_trace"]["children"]) == 0
        assert logged_data["payload"]["stack_trace"]["parents"][0]["fn_name"] == "<module>"

        assert logged_data_2["payload"]["function"]["name"] == "test_tracer_stack_trace_exception.<locals>.test_fn"
        assert logged_data_2["payload"]["function"]["type"] == "Function"
        assert logged_data_2["payload"]["function"]["args"] == ["x", "y", "n"]
        assert logged_data_2["payload"]["status"] == "success"
        assert logged_data_2["payload"]["output"] == payload_2

        assert len(logged_data_2["payload"]["stack_trace"]["parents"]) == 1
        assert len(logged_data_2["payload"]["stack_trace"]["children"]) == 0
        assert logged_data_2["payload"]["stack_trace"]["parents"][0]["fn_name"] == "<module>"
        
    os.remove(filepath)
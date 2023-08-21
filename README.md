# Impulse

This is a minimalist, performance-focused tracing framework for building Python applications, particularly those involving LLM chains. We built this while refining LLM applications to be production-ready, and we didn't want to commit to opinionated frameworks from other solution providers. Feel free to file issues or provide feedback: sudowoodo200 [at] gmail [dot] com. 

## Quickstart

### Installation
 - Install from PyPI: `pip install impulse-core`
 - Direct install: `make install`. Note that this is _not_ an editable installation

### Usage

This initializes the objects with default settings

 - `tracer` will use a `LocalLogger`, which writes json records to a file at `.impulselogs/logs_{timestamp}.json`
 - Currently, this also supports logging to a MongoDB database out of the box. Use `MongoLogger` class instead. (See tutorial)
 - `tracer.hook()` will be set to the default thread at `"default"`

```python
from impulse_core import ImpulseTracer

tracer = ImpulseTracer()

@tracer.hook()
def some_function(x: int, y: str = 2) -> str:
    return f"{str(x)} - {y}"

def handle_request():
    tracer.set_session_id("user_abc_session_1")
    some_function(1)

tracer.shutdown() ## needed for local logger to flush the write buffer
```
The record will capture information (under the `"payload"` field of the json record) during the function call:
```javascript
{
    "function": {
        "name" : "some_function",
        ...
    },
    "trace_module": {
        "tracer_id": "asdfase-234234sdafs-aerwer",
        "thread_id": "default",
        "hook_id": "some_function",
        ...
    }
    "call_id": "asfda2323-52sdfasd",
    "timestamps": {
        "start": "2023-08-20 22:05:55.000000",
        "end": "2023-08-20 22:05:56.123456",
        "start_to_end_seconds": "1.123456"
    },
    "arguments": {
        "x": 1,
        "y": 2
    },
    "status": "success",
    "output": "1 - 2",
    ...
}
```

Each record is uniquely identified by 4 fields:
 - A `call` is every single run of the `traced function`, identified by a `call_id` field in the logs. Each `call` also defines a `trace_log()` context. (see below)
 - A `hook` is a decorator for a specific function, identified by `hook_id` argument in the `@tracer.hook()` function. 
 - A `thread` is a collection of `hook`'s, identified by the `thread_id` argument in the `@tracer.hook()` function. 
 - A `module` is an instance of the `ImpulseTracer` class, identified by the `instance_id` attribute and manages a collection of `threads`
 
This works with functions, methods, classmethods, staticmethods, coroutines, and async generators. If an exception occurs, logging will still happen. 

You can trace nested calls by decorating the relevant functions. For instance:

```python
@tracer.hook()
def top_level():
    return intermediate()

def intermediate():
    return some_function(1,1)
```

The log records will preserve the parent-child relationship between `some_function(x,y)` and `top_level()` in the `stack_trace` field. For instance, this will be captured in the `top_level()`'s record:

```javascript
{
    "function": {
        "name" : "top_level",
        ...
    },
    "call_id": "asdfasdf-2352dsafsa",
    ...
    "stack_trace": {
        "parents": [
            ...
        ],
        "children": [
            {
                "fn_name": "some_function",
                "call_id": "asfda2323-52sdfasd" ,
                "trace_module": { ... }
            },
        ]
    }
    ...
}
{
    "function": {
        "name" : "some_function",
        ...
    },
    "call_id": "asfda2323-52sdfasd",
    ...
    "stack_trace": {
        "parents": [
            {
                "fn_name": "top_level",
                "call_id": "asdfasdf-2352dsafsa",
                "trace_module": { ... }
            },
        ],
        "children": [
            ...
        ]
    }

    // ...
}
```

Each `@trace.hook()` creates a context until superceded by a nested hook. 

### Trace Logs

Another simple by powerful feature is the ability to log arbitrary data, timestamped, directly into the context, which is then included as part of the enclosing logging record. The only restriction is that it must be convertible with `json.dumps`.

```python
from impulse_core import trace_log as log

@tracer.hook()
def some_function(x: int, y: str = 2) -> str:
    log("The ents shall march to")
    log({"location": "Isengard"})
    return f"{str(x)} - {y}"
```

These can be accessed in the `"trace_log"` field of the record.

```javascript
{
    "function": {
        "name" : "some_function",
        ...
    },
    ...
    "trace_log": [
        {
            "timestamp": "2023-08-20 22:05:55.000511",
            "payload": "The ents shall march to"
        },
        ...
    ]
}
```

Common use cases include capturing session data when serving web requests and doing more granular logging of function components.

### Tutorial

Apologies for the lack of docs for now. Still drafting it. In its place, a quick tutorial can be found at [tutorial/tutorial.ipynb](./tutorial/tutorial.ipynb). To get started, use the following to boot up a virtual env with a local mongo-db instance.

```bash
make tutorial
```

After you are done, clean up the tutorial assets with
```bash
make shutdown-tutorial
```

## Logging Schema
Detailed overview of the logging schema can be found at [impulse_core/schema.py](./impulse_core/schema.py)
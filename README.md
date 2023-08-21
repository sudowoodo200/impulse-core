# Impulse

This is a minimalist (but powerful) tracing framework for building Python applications, particularly those involving LLMs and AI features. We built this while refining LLM applications to be production-ready because we didn't want to commit to overly opinionated frameworks from other solution providers. We will pull more features from our stack into this if there is interest. Feel free to file issues and reach out for feedback: sudowoodo200 [at] gmail [dot] com+

## Quickstart

### Installation
 - Install from PyPi: `pip install impulse_core`
 - Direct install: `make install`. Note that this is _not_ an editable installation

### Usage

This initializes the objects with default settings

 - `tracer` will use a `LocalLogger`, which writes json records to a file at `.impulselogs/logs_{timestamp}.json`
 - Currently, this supports logging to a MongoDB database out of the box.
 - `tracer.hook()` will be set to the default thread at `"default"`

```python
from impulse_core import ImpulseTracer

tracer = ImpulseTracer()

@tracer.hook()
def some_function(x: int, y: str = 2) -> str:
    return f"{str(x)} - {y}"

some_function(1)
tracer.shutdown() ## needed for local logger to flush the write buffer
```
The record will capture information (under the `"payload"` field of the json record) during the call:
```json
{
    "function": {
        "name" : "some_function"
        ...
    },
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
    "output": "1 - 2"
    ...
}
```

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

```json
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
                "trace_module": {
                    ...
                }
            }
        ]
    }
    ...
}
{
    "function": {
        "name" : "some_function",
        ...
    }
    "call_id": "asfda2323-52sdfasd",
    ...
    "stack_trace": {
        "parents": [
            {
                "fn_name": "top_level",
                "call_id": "asdfasdf-2352dsafsa",
                "trace_module": {
                    ...
                }
            }
        ],
        "children": [
            ...
        ]
    }

    ...
}
```

Each `@trace.hook()` creates a context until superceded by a nested hook. A simple by powerful feature is the ability to log arbitrary data, timestamped, directly into the context, which is then included as part of the enclosing logging record. The only restriction is that it must be convertible with `json.dumps`.

```python
from impulse_core import trace_log as log

@tracer.hook()
def some_function(x: int, y: str = 2) -> str:
    log("The ents shall march to")
    log({"location": "Isengard"})
    return f"{str(x)} - {y}"
```

These can be accessed in the `"trace_log"` field of the record.

```json
{
    "function": {
        "name" : "some_function"
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

Common use cases include capturing session data when serving web requests and doing more granular logging of function components.
```

### Tutorial

A quick tutorial can be found at `tutorial/tutorial.ipynb`. To get started, use the following to boot up a virtual env with a local mongo-db instance.

```bash
make tutorial
```

After you are done, clean up the tutorial assets with
```bash
make shutdown-tutorial
```

## Logging Schema
Detailed overview of the logging schema can be found at [impulse_core/schema.py](./impulse_core/schema.py)
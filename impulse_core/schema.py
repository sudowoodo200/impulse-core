from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union, Optional
from datetime import datetime

class TracedFunctionSchema(BaseModel):
    type: str
    name: str
    args: List[str]

class TraceModuleSchema(BaseModel):
    tracer_id: str
    tracer_metadata: Dict[str, Any]
    thread_id: str
    hook_id: str
    hook_metadata: Dict[str, Any]

class FunctionTimestampsSchema(BaseModel):
    start: datetime
    end: datetime
    start_to_end_seconds: Optional[float] = None

class FunctionArgumentsSchema(BaseModel):
    args: Dict[str, Any]
    kwargs: Dict[str, Any]
    instance_attr: Optional[Dict[str, Any]] = None

class ContextNodeSchema(BaseModel):
    fn_name: str
    call_id: str
    trace_module: Optional[TraceModuleSchema] = None

class StackTraceSchema(BaseModel):
    parents: List[ContextNodeSchema]
    children: List[ContextNodeSchema] 

class TraceLogSchema(BaseModel):
    timestamp: datetime
    payload: Union[str, Dict[str, Any]]

class TraceSchema(BaseModel):
    function: TracedFunctionSchema
    trace_module: TraceModuleSchema
    call_id: str
    timestamps: FunctionTimestampsSchema
    arguments: FunctionArgumentsSchema
    status: str
    exception: Optional[str] = None
    output: Optional[Any] = None
    stack_trace: Optional[StackTraceSchema] = None
    trace_logs: Optional[List[TraceLogSchema]] = None


EMPTY_TRACE_TEMPLATE = {
    "function": {
        "type": "",
        "name": "",
        "args": []
    },
    "trace_module": {
        "tracer_id": "",
        "tracer_metadata": {
            "tracing_context": ""
        },
        "thread_name": "",
        "hook_id": "",
        "hook_metadata": {}
    },
    "call_id": "",
    "timestamps": {
        "start": "",
        "end": "",
    },
    "arguments": {
        "args": {},
        "kwargs": {},
        "instance_attr": {}
    },
    "status": "",
    "output": "",
    "stack_trace": {
        "parents": [],
        "children": []
    },
    "trace_logs": []
}


if __name__ == "__main__":

    data = {
        "function": {
            "type": "AsyncGenerator",
            "name": "TestClass.count",
            "args": [
                "self",
                "n"
            ]
        },
        "trace_module": {
            "tracer_id": "impulse_module_af562891",
            "tracer_metadata": {
                "tracing_context": "unit_test"
            },
            "thread_name": "test",
            "hook_id": "impulse_hook_d9428c38",
            "hook_metadata": {}
        },
        "call_id": "a9161872-d83b-42ea-8aee-75ba8ce71e5e",
        "timestamps": {
            "start": "2023-08-18 20:11:11.409751",
            "end": "2023-08-18 20:11:11.409840",
            "start_to_end_seconds": "0.000089"
        },
        "arguments": {
            "args": {
                "self": "TestClass(x=1, y=2)",
                "n": 5
            },
            "kwargs": {},
            "instance_attr": {
                "x": 1
            }
        },
        "status": "success",
        "output": "13579",
        "stack_trace": {
            "fn_name": "TestClass.count",
            "call_id": "a9161872-d83b-42ea-8aee-75ba8ce71e5e",
            "trace_module": {
                "tracer_id": "impulse_module_af562891",
                "tracer_metadata": {
                    "tracing_context": "unit_test"
                },
                "thread_name": "test",
                "hook_id": "impulse_hook_d9428c38",
                "hook_metadata": {}
            },
            "parents": [
                {
                    "fn_name": "<module>",
                    "call_id": "789a1d7e-56c1-4e63-bd61-9a31505d156f",
                    "trace_module": {
                        "tracer_id": "",
                        "tracer_metadata": {},
                        "thread_name": "",
                        "hook_id": "",
                        "hook_metadata": {}
                    }
                }
            ],
            "children": []
        },
        "trace_logs": [
            {
                "timestamp": "2023-08-18 20:11:11.409790",
                "payload": "Counting 0"
            },
            {
                "timestamp": "2023-08-18 20:11:11.409813",
                "payload": "Counting 1"
            },
            {
                "timestamp": "2023-08-18 20:11:11.409818",
                "payload": "Counting 2"
            },
            {
                "timestamp": "2023-08-18 20:11:11.409823",
                "payload": "Counting 3"
            },
            {
                "timestamp": "2023-08-18 20:11:11.409829",
                "payload": "Counting 4"
            }
        ]
    }

    trace_instance = Trace(**data)
    print(trace_instance)
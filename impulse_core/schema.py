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
    arguments: Dict[str, Any]
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
        "thread_id": "",
        "hook_id": "",
        "hook_metadata": {}
    },
    "call_id": "",
    "timestamps": {
        "start": "",
        "end": "",
    },
    "arguments": {},
    "status": "",
    "output": "",
    "stack_trace": {
        "parents": [],
        "children": []
    },
    "trace_logs": []
}
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union, Optional
from datetime import datetime

class TracedFunctionSchema(BaseModel):
    type: str
    name: str
    args: Optional[List[str]] = None

class TraceModuleSchema(BaseModel):
    tracer_id: str
    session_id: str
    thread_id: str
    hook_id: str
    tracer_metadata: Dict[str, Any]
    session_metadata: Optional[Dict[str, Any]] = None
    hook_metadata: Optional[Dict[str, Any]] = None

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
    feedback: Optional[Dict[str, Any]] = None


EMPTY_TRACE_TEMPLATE = {
    "function": {
        "type": "",
        "name": "",
        "args": []
    },
    "trace_module": {},
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
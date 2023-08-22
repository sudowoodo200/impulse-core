from __future__ import annotations
from contextlib import contextmanager
import contextvars as cv
import inspect
import json, os, sys, time, uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Union, Callable, Tuple
from enum import Enum
import asyncio
import functools as ft, hashlib

from impulse_core.logger import BaseAsyncLogger, LocalLogger, MongoLogger
from impulse_core.schema import TraceSchema, EMPTY_TRACE_TEMPLATE

@dataclass
class ImpulseTraceNode:
    
    name: str
    call_id: str
    trace_module: Optional[Dict[str, Any]]
    creation_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    parents: List[ImpulseTraceNode] = field(default_factory=list)
    children: List[ImpulseTraceNode] = field(default_factory=list)
    trace_logs: List[Dict[str, Any]] = field(default_factory=list)
    diff_process: bool = False

    def add_child(self, child_node: ImpulseTraceNode):
        self.children.append(child_node)
        child_node.parents.append(self)

    def export(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:

        # Handles multiprocessing
        for parent in self.parents:
            if self not in parent.children:
                self.diff_process = True
                parent.children.append(self)

        return {
            "parents": [parent.export_node() for parent in self.parents],
            "children": [child.export_node() for child in self.children]
        }, self.trace_logs

    def export_node(self) -> Dict[str, Any]:
        return {
            "fn_name": self.name,
            "call_id": self.call_id,
            "trace_module": self.trace_module,
        }

curr_frame = inspect.currentframe()
if curr_frame is not None:
    root_name = curr_frame.f_code.co_name
else: 
    root_name = "<module>"

IMPULSE_GLOBAL_ROOT = ImpulseTraceNode(
    name = root_name,
    call_id = str(uuid.uuid4()),
    creation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
    trace_module = None
)
IMPULSE_CURRENT_TRACE_ROOT: cv.ContextVar[ImpulseTraceNode] = cv.ContextVar("IMPULSE_CURRENT_TRACE_ROOT", default=IMPULSE_GLOBAL_ROOT)

@contextmanager
def impulse_trace_context(new_root: ImpulseTraceNode):
    """
    Context manager for tracing.
    """
    old_root: ImpulseTraceNode = IMPULSE_CURRENT_TRACE_ROOT.get()
    if old_root is not None:
        old_root.add_child(new_root)
    IMPULSE_CURRENT_TRACE_ROOT.set(new_root)
    try:
        yield
    except Exception as e:
        raise e
    finally:
        IMPULSE_CURRENT_TRACE_ROOT.set(old_root)

def trace_log(payload: Union[str, Dict[str, Any]], printout: bool = True):
    """
    Log payload into the trace context
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    curr_root = IMPULSE_CURRENT_TRACE_ROOT.get()
    if curr_root is not None:
        curr_root.trace_logs.append({
            "timestamp": now,
            "payload": payload
        })
    else:
        raise Exception("No trace context available.")
    
    if printout:
        print(f"[TRACE LOG] {curr_root.name}() @ {now} : {payload}")


STANDARD_TYPES = (int, float, str, bool, list, dict, tuple, set, frozenset, type(None))

def conform_output(obj: Any) -> Union[str,Dict[str, Any]]:
    try:
        json.dumps(obj)
        return obj
    except:
        try:
            return str(obj)
        except:
            return "No logging representation available."

@dataclass
class ImpulseTracer:

    logger: BaseAsyncLogger = field(default_factory=LocalLogger)
    metadata: Dict[str, Any] = field(default_factory=dict)
    instance_id: Optional[str] = None
    session_id: Optional[str] = None
    session_metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.instance_id is None:
            self.instance_id = "impulse_module_"+str(uuid.uuid4())[:8]
        if self.session_id is None:
            self.session_id = "run_" + datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

    def set_session_id(self, session_id: str, session_metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Set the session id.
        """
        self.session_id = session_id
        self.session_metadata = session_metadata

    def hook(self,
            thread_id: str = "default", 
            hook_id: Optional[str] = None,
            hook_metadata: Dict[str, Any] = {},
            output_postprocess: Optional[Callable] = None) -> Callable:

        def decorator(func: Callable) -> Callable:
            """
            Decorator for logging various objects.
            
            Captures the following fields:
                - the function name, arguments, instance attributes, and return value 
                - timestamps, time to complete call
                - relation to other traced functions
            """

            f_name: str = func.__qualname__
            f_args: List[str] = inspect.getfullargspec(func).args
            nonlocal hook_id

            if hook_id is None:
                hook_id = f_name

            IS_COROUTINE = inspect.iscoroutinefunction(func) 
            IS_ASYNCGEN = inspect.isasyncgenfunction(func) 

            trace_output: dict = {}
            trace_output["function"] = {
                "type": "Coroutine" if IS_COROUTINE else "AsyncGenerator" if IS_ASYNCGEN else "Function",
                "name": f_name,
                "args" : f_args
            }
            trace_output["trace_module"] = {
                "tracer_id": self.instance_id,
                "session_id": self.session_id,
                "thread_id": thread_id,
                "hook_id": hook_id,
                "tracer_metadata": self.metadata,
                "session_metadata": self.session_metadata,
                "hook_metadata": hook_metadata
            }

            def trace_init(*args, **kwargs) -> ImpulseTraceNode:
                trace_output.update({
                    **self._initialize_call(),
                    **self._get_time("start"),
                    **self._process_inputs(inspect.signature(func), args, kwargs)
                })
                new_root = ImpulseTraceNode(
                    name = f_name,
                    call_id = trace_output["call_id"],
                    creation_time=trace_output["timestamps"]["start"],
                    trace_module = trace_output["trace_module"]
                )
                return new_root

            def trace_complete(new_root: ImpulseTraceNode) -> None:
                trace_output.update(self._get_time("end", trace_output["timestamps"], delta_to="start"))
                trace_output["stack_trace"], trace_output["trace_logs"] = new_root.export() 
                self._write(payload=trace_output)

            @ft.wraps(func)
            async def coro_wrapper(*args, **kwargs):
                """
                Asynchronous coroutine wrapper.
                """
                new_root = trace_init(*args, **kwargs)
                
                try:
                    output = None
                    with impulse_trace_context(new_root):
                        output = await func(*args, **kwargs)
                    
                    trace_output["status"] = "success"

                    if output_postprocess is not None:
                        output = output_postprocess(output)

                    trace_output["output"] = self._parse_item(output)

                except Exception as e:
                    trace_output["status"] = "error"
                    self._handle_exception(e, trace_output)

                finally:
                    trace_complete(new_root)

                return output
            
            @ft.wraps(func)
            async def agen_wrapper(*args, **kwargs):
                """
                Asynchronous generator wrapper.
                """
                new_root = trace_init(*args, **kwargs)

                try:
                    output = []
                    with impulse_trace_context(new_root):
                        async for chunk in func(*args, **kwargs):
                            yield chunk
                            output.append(chunk)
                    
                    if all([isinstance(output[i], str) for i in range(len(output))]):
                        output = "".join(output)
                    
                    if output_postprocess is not None:
                        output = output_postprocess(output)

                    trace_output["status"] = "success"
                    trace_output["output"] = self._parse_item(output)

                except Exception as e:
                    trace_output["status"] = "error"
                    trace_output["output"] = output
                    self._handle_exception(e, trace_output)
                
                finally:
                    trace_complete(new_root)

            @ft.wraps(func)
            def wrapper(*args, **kwargs):
                """
                Synchronous function call wrappers.
                """
                new_root = trace_init(*args, **kwargs)
                
                try:
                    output = None
                    with impulse_trace_context(new_root):
                        output = func(*args, **kwargs)

                    trace_output["status"] = "success"
                    if output_postprocess is not None:
                        output = output_postprocess(output)
                        
                    trace_output["output"] = self._parse_item(output)
                    
                except Exception as e:
                    trace_output["status"] = "error"
                    self._handle_exception(e, trace_output)
                
                finally:
                    trace_complete(new_root)

                return output

            if IS_COROUTINE:
                return coro_wrapper
            elif IS_ASYNCGEN:
                return agen_wrapper
            else:
                return wrapper
            
        return decorator

    def classhook(self,
            thread_id: str = "default", 
            traced_methods: List[str] = field(default_factory=list),
            hook_ids: Optional[Union[str, Dict[str, str]]] = None,
            hook_metadata: Dict[str, Any] = {},
            output_postprocess: Optional[Dict[str,Callable]] = None) -> type:
        
        if len(traced_methods) == 0:
            traced_methods = ["__call__"]

        def decorate(cls: type) -> type:
        
            class_name = cls.__name__

            for method in traced_methods:
                if method not in cls.__dict__:
                    print(f"[TRACE WARNING]: {method} not found in {class_name}.")
                if method not in hook_ids:
                    hook_ids[method] = getattr(cls, method).__qualname__
            
            # TODO: call hook on each method

        raise NotImplementedError("Class decorator not yet implemented.")
    
    def _initialize_call(self) -> Dict[str, Any]:
        output = {}
        output["call_id"] = str(uuid.uuid4())
        return output

    def _get_time(self, 
                  field_name: str, 
                  past_times: Dict[str,str] = {}, 
                  delta_to: Optional[str] = None) -> Dict[str, Any]:
        
        now: datetime = datetime.now()
        output = {"timestamps": {field_name: now.strftime("%Y-%m-%d %H:%M:%S.%f"), **past_times}}

        if delta_to is not None:
            timestamp = past_times[delta_to]
            delta = now - datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
            output["timestamps"][f"{delta_to}_to_{field_name}_seconds"] = f"{delta.total_seconds():.6f}"
        return output

    def _process_inputs(self,
                        sig: inspect.Signature,
                        args: Tuple[Any, ...],
                        kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the arguments to be logged.
        Output written to the output dict.
         - If the function is a method, log the instance attributes.
        """
        output = {}
        bound_args: inspect.BoundArguments = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
    
        arguments = {k: self._parse_item(v) for k, v in bound_args.arguments.items()}
            
        output["arguments"] = arguments

        return output

    def _parse_item(self, item: Any) -> Union[str,Dict[str, Any]]:
        """
        Parse the item to be logged.
         - Try __str__() and __repr__() otherwise.
         - If json.dumps() is successful, return the item as a dict.
         - If both fail, return "No logging representation available."
        """

        # TODO: Add support for att
        if hasattr(item, '__class__') and not isinstance(item, STANDARD_TYPES):

            is_instance: bool = (not inspect.isbuiltin(item)) and item.__class__.__name__ != "type"
            if not is_instance:
                assert inspect.isclass(item), "Item is not a class or instance."

            return {
                "type": "instance" if is_instance else "class",
                "classname": item.__class__.__name__ if is_instance else item.__name__,
                "attr": {k: conform_output(v) for k, v in self._process_attr(item).items()}
            }
        
        else:
            return conform_output(item)

    def _process_attr(self, 
                    method_instance: Any) -> Dict[str, Any]:
        """
        Process the instance/method attributes to be logged.
         - If instance_attr is None, log all non-method attributes.
         - If instance_attr is not None, log only the attributes in instance_attr.
        """
        incld_instance_attr = [ attr 
                                for attr in dir(method_instance) 
                                if not callable(getattr(method_instance, attr)) 
                                and not attr.startswith('__') ]
        return {
            attr: conform_output(getattr(method_instance, attr)) 
            for attr in incld_instance_attr
        }   

    def _handle_exception(self, e: Exception,
                     trace_output: Optional[Dict[str, Any]] = None) -> None:
        """
        Throw an error.
        """
        if trace_output is not None:
            trace_output["exception"] = f"{e}"
            trace_output.update(self._get_time("end", trace_output["timestamps"], delta_to="start"))

        raise e

    def _write(self, 
               payload: Dict[str, Any]) -> None:
        """
        Validate and write the payload to the logger.
        """
        try:
            TraceSchema(**payload)
        except Exception as e:
            print(f"[TRACE WARNING]: Payload does not conform to Trace schema: {e}")
        finally:
            self.logger.log(payload=payload, metadata={"source": "impulse_tracer"})

    def _flush_global_root(self):
        """
        Flush the global root.
        """
        assert IMPULSE_GLOBAL_ROOT is not None, "Global root context not found."
        output = EMPTY_TRACE_TEMPLATE.copy()
        output["function"] = {
            "type": "Function",
            "name": IMPULSE_GLOBAL_ROOT.name,
            "args": []
        }
        output["trace_module"] = {
            "tracer_id": self.instance_id,
            "session_id": self.session_id,
            "thread_id": "root",
            "hook_id": "global_root",
            "tracer_metadata": self.metadata,
            "session_metadata": self.session_metadata,
            "hook_metadata": {}
        }
        output["call_id"] = IMPULSE_GLOBAL_ROOT.call_id
        output["timestamps"]= {
            "start": IMPULSE_GLOBAL_ROOT.creation_time,
            "end": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }
        output["stack_trace"], output["trace_logs"] = IMPULSE_GLOBAL_ROOT.export()
        output["status"] = "success"
        output["output"] = None
        output["exception"] = None

        self._write(payload=output)

    def shutdown(self, flush_global_root: bool = True) -> None:
        """
        Shutdown the tracer.
        """
        if flush_global_root:
            self._flush_global_root()

        self.logger.shutdown()
        

if __name__ == "__main__":

    logger = LocalLogger()
    tracer = ImpulseTracer()

    @tracer.hook(thread_id="test_thread")
    def test_func(a: int, b: int, c: int = 1) -> int:
        return a + b + c
    
    test_func(1, 2, 3)

    tracer.shutdown()
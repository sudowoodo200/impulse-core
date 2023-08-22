from datetime import datetime
import json
from typing import Any, Dict, List
import streamlit as st
import extra_streamlit_components as stx
from st_ant_tree import st_ant_tree

from utils import mdb

st.set_page_config(layout="wide", page_title="Impulse", page_icon = "assets/images/favicon.png")
app = st.container()

URI = "mongodb://root:example@localhost:27017/"
DATABASE = "impulse"
mdb_client = mdb.get_mdb_client(URI)
db = mdb_client[DATABASE]

## Session state
def get_session_var(name: str) -> Any:
    if name not in st.session_state:
        st.session_state[name] = False
        return False
    else:
        return st.session_state[name]

def set_session_var(name: str, value: Any = True):
    st.session_state[name] = value

def init_session_var(name: str, value: Any = True):
    if name not in st.session_state:
        st.session_state[name] = value

def read_node(node: Dict[str, Any]):

            output = node["payload"]
            return output

def get_by_call_id(fns:List[Dict[str, Any]], call_id: str) -> Dict[str, Any]:
    for fn in fns:
        if fn["call_id"] == call_id:
            return fn
    return None

def format_name(node: str) -> str:
    name = node["function"]["name"] if node["function"]["name"] != "<module>" else "root"
    args = ", ".join([f"{k}" for k in node["arguments"].keys()])
    return f"{name}({args})"

# https://flucas96-streamlit-tree-select-example-app-s0vkjx.streamlit.app/
def gen_tree(root: Dict[str, Any], fns: List[Dict[str, Any]]):
    if root["stack_trace"]["children"] == []:
        return {
            "title": format_name(root),
            "value": json.dumps({k: v for k,v in root.items() if k != "stack_trace"})
        }
    else:
        children = []
        thread_set = [f["call_id"] for f in fns]
        for child in root["stack_trace"]["children"]:
            if child["call_id"] not in thread_set:
                continue
            child_node = get_by_call_id(fns, child["call_id"])
            children.append( child_node)
    
        return {
            "title": format_name(root),
            "value": json.dumps({k: v for k,v in root.items() if k != "stack_trace"}),
            "children": [ gen_tree(child, fns) for child in children ]
        }

with app:

    st.title('Impulse')

    ## Add a sidebar
    with st.sidebar:

        collections = db.list_collection_names()
        collection_name = st.selectbox("Select a collection", options=collections)
        set_session_var("collection", collection_name)
        collection = db[collection_name]
        if collection is not None:

            
            if get_session_var("anchored"):
                threads = collection.distinct("payload.trace_module.thread_id", 
                                          {"payload.function.name": get_session_var("anchor")})
            else:
                threads = collection.distinct("payload.trace_module.thread_id")
            
            
            threads = [t for t in threads if t != "root"]
            thread = st.selectbox("Select a thread", options=threads)

            if get_session_var("anchored"):
                sessions = collection.distinct("payload.trace_module.session_id",
                                               {"payload.function.name": get_session_var("anchor")})
                
            else:
                sessions = collection.distinct("payload.trace_module.session_id")

            old_sessions = sessions
            session = st.selectbox("Select a session", options=sessions)

            # idx = sessions.index(session)
            # n = len(sessions)
            # col1, col2 = st.columns([1, 1])
            # col2.button("Previous", on_click= lambda: set_session_var("session_idx", (idx - 1) % n))
            # col1.button("Next", on_click= lambda: set_session_var("session_idx", (idx + 1) % n))

            fns = collection.find({"payload.trace_module.session_id": session,
                                    "payload.trace_module.thread_id": thread},
                                    projection={"payload": 1, "_id": 0})
            
            if get_session_var("anchored"):

                root = collection.find({"payload.trace_module.session_id": session,
                                    "payload.function.name": get_session_var("anchor")},
                                    projection={"payload": 1, "_id": 0})

            else:
                root = collection.find({"payload.trace_module.session_id": session,
                                    "payload.trace_module.thread_id": "root"},
                                    projection={"payload": 1, "_id": 0})
            
            fns = list(fns)
            root = list(root)[0]
            
            # Selection
            root = read_node(root)
            fns = [read_node(fn) for fn in fns]
            tree = [gen_tree(root, fns)]

            "---"

            st.write("**Trace Tree**")

            # Display
            chosen_node = st_ant_tree(treeData=tree, allowClear= True, bordered= True, filterTreeNode= True, 
                            multiple= False, placeholder= "Select Trace Node", showArrow= True, showSearch= False, treeCheckable= False, 
                            width_dropdown= "100%", disabled= get_session_var("anchored"))
            
            if chosen_node is not None:

                if get_session_var("anchored"):
                    chosen_node = root
                else:
                    chosen_node = json.loads(chosen_node)
            
                if st.button("Anchor"):
                    method_name = chosen_node["function"]["name"]
                    set_session_var("anchor", method_name)
                    set_session_var("anchored", True)

            "---"
    
    "---"

     ## Add a main page
    with st.container():

        if chosen_node is not None:

            start_time = datetime.strptime(chosen_node["timestamps"]["start"], "%Y-%m-%d %H:%M:%S.%f")
            end_time = datetime.strptime(chosen_node["timestamps"]["end"], "%Y-%m-%d %H:%M:%S.%f")
            call_time = end_time - start_time
            st.write("**Call Time**: %2f seconds" % call_time.total_seconds())

            st.write("**Status**: %s" % chosen_node["status"])

        col1, col2 = st.columns([1, 1])

        if chosen_node is not None:

            with col1:
                if "arguments" in chosen_node:
                    st.text_area("Input", value=json.dumps(chosen_node["arguments"], indent=4), height=400)

            with col2:
                if chosen_node["status"] == "success":
                    st.text_area("Output", value=json.dumps(chosen_node["output"], indent=4), height=400)
                else:
                    st.text_area("Output", value=json.dumps(chosen_node["exception"], indent=4), height=400)

            "---"
            
            with st.container():
                if len(chosen_node["trace_logs"]) > 0:
                    st.text_area("Trace", value=json.dumps(chosen_node["trace_logs"], indent=4), height=200)
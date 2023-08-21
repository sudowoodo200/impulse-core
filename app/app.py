from typing import Any
import streamlit as st
import extra_streamlit_components as stx
# from st_ant_tree import st_ant_tree

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

with app:

    st.title('Impulse')

    ## Add a sidebar
    with st.sidebar:

        collections = db.list_collection_names()
        collection_name = st.selectbox("Select a collection", options=collections)
        set_session_var("collection", collection_name)
        collection = db[collection_name]
        if collection is not None:
            
            sessions = collection.distinct("payload.trace_module.session_id")
            session = st.selectbox("Select a session", options=sessions)
            
            threads = collection.distinct("payload.trace_module.thread_id", 
                                          {"payload.trace_module.session_id": session})
            thread = st.selectbox("Select a thread", options=threads)

            data = list[collection.find({"payload.trace_module.tracer_id": tracer_id,
                                    "payload.trace_module.session_id": session,
                                    "payload.trace_module.thread_id": thread},
                                    projection={"payload": 1, "_id": 0})]
            
            set_session_var("data", data)
    
    "---"

     ## Add a main page
    with st.container():

        # Selection
        data = get_session_var("data")
        root = get_root(data)
        tree = gen_tree(root, data)

        # Display
        col1, col2 = st.columns([1, 1])
        with col1:
            st.write("Inputs")

        with col2:
            st.write("Outputs")

        "---"
        
        with st.container():
            st.write("Trace Logs")
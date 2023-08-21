import streamlit as st
import extra_streamlit_components as stx

st.set_page_config(layout="wide", page_title="Impulse", page_icon = "assets/images/favicon.png")
app = st.container()

with app:

    st.title('Impulse')

    ## Add a sidebar
    with st.sidebar:

        st.title("Select session id")
    
    "---"

     ## Add a main page
    with st.container():

        col1, col2 = st.columns([1, 1])
        with col1:
            st.write("Inputs")

        with col2:
            st.write("Outputs")

        "---"
        
        with st.container():
            st.write("Trace Logs")
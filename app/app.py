import streamlit as st
import extra_streamlit_components as stx

st.set_page_config(layout="wide", page_title="Impulse", page_icon = "assets/images/favicon.png")
app = st.container()

with app:

    st.title('Impulse')

    ## Add a sidebar
    with st.sidebar:

        st.title("Trace Tree")
    
    "---"

     ## Add a main page
    with st.container():

        col1, col2 = st.columns([1, 5])
        with col1:
            st.write("ABC")

        with col2:
            st.write("XYZ")
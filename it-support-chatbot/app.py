import streamlit as st
import os
from pathlib import Path
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

# --- Streamlit UI Setup ---
st.set_page_config(page_title="IT Support Chatbot", layout="wide")
st.title("🛠️ IT Support Engineer – Notes Chatbot")

# --- Sidebar API Key ---
openai_api_key = st.sidebar.text_input("🔑 Enter your OpenAI API Key", type="password")

# --- Ensure notes/ folder exists ---
NOTES_DIR = Path("notes")
NOTES_DIR.mkdir(exist_ok=True)

# --- Upload Notes ---
uploaded_file = st.sidebar.file_uploader("📤 Upload a .txt notes file", type="txt")

if uploaded_file is not None:
    file_path = NOTES_DIR / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Uploaded: {uploaded_file.name}")

# --- Load Notes Dynamically ---
def load_notes():
    docs = []
    txt_files = list(NOTES_DIR.glob("*.txt"))

    st.write("📁 Files found in notes/:", [f.name for f in NOTES_DIR.glob("*")])  # Debug

    if not txt_files:
        st.warning("⚠️ No .txt files found inside the 'notes/' folder.")
        return docs

    for file in txt_files:
        st.info(f"📄 Loaded: {file.name}")
        loader = TextLoader(str(file), encoding="utf-8")
        docs.extend(loader.load())

    return docs

# --- Build QA System ---
@st.cache_resource(show_spinner="🔍 Indexing your notes...")
def setup_qa():
    documents = load_notes()
    if not documents:
        return None

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = splitter.split_documents(documents)
    if not texts:
        st.warning("⚠️ Your notes were found but couldn't be split into readable chunks.")
        return None

    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = FAISS.from_documents(texts, embeddings)
    retriever = vectorstore.as_retriever()

    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(openai_api_key=openai_api_key),
        chain_type="stuff",
        retriever=retriever
    )
    return qa_chain

# --- Main App Logic ---
if openai_api_key:
    qa = setup_qa()

    if qa:
        query = st.text_input("💬 Ask something from your notes:")
        if query:
            with st.spinner("🤖 Thinking..."):
                try:
                    response = qa.run(query)
                    st.success(response)
                except Exception as e:
                    st.error(f"❌ Error: {e}")
else:
    st.info("💡 Please enter your OpenAI API key in the sidebar to begin.")





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
st.title("🛠️ IT Support Engineer - Notes Chatbot")

# --- API Key Input ---
openai_api_key = st.sidebar.text_input("🔑 Enter your OpenAI API Key", type="password")

# --- Load Notes ---
def load_notes():
    docs = []
    notes_path = Path("notes")
    if not notes_path.exists():
        st.warning("No 'notes/' folder found. Please create one and add .txt files.")
        return docs

    files = list(notes_path.glob("*.txt"))
    if not files:
        st.warning("No .txt files found in the 'notes/' folder.")
        return docs

    for file in files:
        loader = TextLoader(str(file), encoding="utf-8")
        docs.extend(loader.load())
    return docs

# --- Build QA Chain ---
@st.cache_resource(show_spinner="Indexing notes...")
def setup_qa():
    documents = load_notes()
    if not documents:
        return None

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = splitter.split_documents(documents)
    if not texts:
        st.warning("Your notes are loaded, but no readable chunks were created.")
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
            with st.spinner("Searching your notes..."):
                try:
                    response = qa.run(query)
                    st.success(response)
                except Exception as e:
                    st.error(f"An error occurred while processing the query:\n{e}")
else:
    st.info("Please enter your OpenAI API key in the sidebar to begin.")




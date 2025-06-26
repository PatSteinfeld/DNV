import streamlit as st
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
import os
from pathlib import Path

# --- Streamlit UI ---
st.set_page_config(page_title="IT Support Chatbot", layout="wide")
st.title("🛠️ IT Support Engineer - Notes Chatbot")

# --- API Key ---
openai_api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")

# --- Load and Process Notes ---
def load_notes():
    docs = []
    notes_path = Path("notes")
    for file in notes_path.glob("*.txt"):
        loader = TextLoader(str(file), encoding="utf-8")
        docs.extend(loader.load())
    return docs

# --- Setup QA chain ---
@st.cache_resource(show_spinner="Indexing notes...")
def setup_qa():
    documents = load_notes()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = FAISS.from_documents(texts, embeddings)
    retriever = vectorstore.as_retriever()
    qa = RetrievalQA.from_chain_type(llm=ChatOpenAI(openai_api_key=openai_api_key),
                                     chain_type="stuff",
                                     retriever=retriever)
    return qa

if openai_api_key:
    qa = setup_qa()

    # --- User Query ---
    query = st.text_input("Ask a question based on your notes:")
    if query:
        with st.spinner("Searching your notes..."):
            result = qa.run(query)
            st.success(result)
else:
    st.warning("Please enter your OpenAI API key in the sidebar.")


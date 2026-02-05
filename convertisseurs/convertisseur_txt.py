import os
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

OPENWEBUI_URL = "https://chat.ai-labs.helmo.be"
API_KEY = "sk-a6a2056cf5b44080b8df36e6126914e1"

os.environ["OPENAI_API_KEY"] = API_KEY

llm = ChatOpenAI(
    model="gpt-oss:120b",
    base_url=f"{OPENWEBUI_URL}/api",
    api_key=API_KEY,
    temperature=0
)

# Création modèle embeddings (petit modèle local)
print("Chargement du modèle d'embedding...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Créons un fichier texte exemple pour le test
with open("test_knowledge.txt", "w", encoding="utf-8") as f:
    f.write("Le projet Apollo 11 a permis aux humains de marcher sur la Lune en 1969. Neil Armstrong était le commandant.")

# Chargement
loader = TextLoader("./test_knowledge.txt", encoding="utf-8")
docs = loader.load()

# Découpage (Chunking)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
splits = text_splitter.split_documents(docs)

# Stockage dans ChromaDB (Base locale)
print("Création de la base vectorielle...")
vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

# --- 4. Interroger la base (RAG) ---
from langchain.chains import RetrievalQA

print("Initialisation de la chaîne de RAG...")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 2})
)

# --- 5. Test ---
query = "Qui était le commandant de la mission Apollo 11 ?"
print(f"\nQuestion : {query}")
response = qa_chain.invoke(query)

print("\nRéponse de l'IA :")
print(response["result"])
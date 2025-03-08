import os
from pathlib import Path
from dotenv import load_dotenv

from langchain import hub
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict

load_dotenv()

def get_chat_model(model_name: str, provider:str, **kwargs):

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name)
    
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            model_name=model_name,
            # model_kwargs={
            #     "headers": {
            #         "HTTP-Referer": getenv("YOUR_SITE_URL"),
            #         "X-Title": getenv("YOUR_SITE_NAME"),
            #     }
            # },
        )
    
    else:
        raise ValueError(f"Unknown model provider: {provider}")

llm = get_chat_model("google/gemini-2.0-flash-thinking-exp:free", "openrouter")
# messages = [
#     SystemMessage(content="You are a helpful assistant."),
#     HumanMessage(content="Hi there"),
# ]
# output = llm.invoke(messages)
# print(output)

def load_documents(filepaths: List[str]) -> List[Document]:
    documents = []
    for filepath in filepaths:
        if not os.path.exists(filepath):
            print(f"File {filepath} does not exist.")
            continue

        if filepath.endswith(".pdf"):
            loader = PyPDFLoader(filepath)
            documents.extend(loader.load())
        
        elif filepath.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as file:
                content = file.read()
                documents.append(Document(page_content=content))
        else:
            print(f"Unsupported file type for {filepath}. Only PDF and TXT are supported.")
    return documents

# loading documets from raw format
dir_path = Path("assets/tmp")
dir_contents_path = [str(file) for file in dir_path.iterdir() if file.is_file()]
# print(dir_contents_path)
documents = load_documents(dir_contents_path)
print(len(documents))


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=200, add_start_index=True
)
all_splits = text_splitter.split_documents(documents)
print(f"Total splits: {len(all_splits)}")

# convert text to embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vector_store = Chroma(embedding_function=embeddings)
vector_store.add_documents(documents=all_splits)

# Define state for application
class State(TypedDict):
    question: str
    context: List[Document]
    answer: str


def retrieve(state: State):
    retrieved_docs = vector_store.similarity_search(state["question"])
    return {"context": retrieved_docs}

prompt = hub.pull("rlm/rag-prompt")
def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = llm.invoke(messages)
    return {"answer": response.content}

graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()

response = graph.invoke({"question": "How many stores are there for nike?"})
print(response["answer"])
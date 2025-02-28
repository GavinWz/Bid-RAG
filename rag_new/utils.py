import logging
import os

from langchain_ollama import ChatOllama
from openai import OpenAI
from langchain_milvus import Milvus, Zilliz
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings

from rag.config import Config


def load_config():
    config = Config()
    return config


def load_embedding_model(config: Config):
    embedding_model_dir = config.embedding_model_dir
    embedding_model_name = config.embedding_model_name
    embedding_model_path = os.path.join(embedding_model_dir, embedding_model_name)
    embedding_model = HuggingFaceEmbeddings(
        model_name=embedding_model_path,
        model_kwargs={'device': 'cuda'}
    )
    logging.info(f"Embedding model loaded successfully from {embedding_model_path}.")
    return embedding_model


def load_vec_db(config, embedding_model):
    index_params = {
        "field_name": "vector",  # 向量字段名称
        "index_type": "HNSW",  # 索引类型
        "index_name": "ivf_flat_index",  # 索引名称
        "metric_type": "COSINE"
    }
    db_client = Milvus(
        embedding_function=embedding_model,
        collection_name=config.collection_name,
        auto_id=True,
        drop_old=True,  # 如果已存在同名 Collection，是否删除重建
        index_params=index_params
    )
    return db_client


def load_everything():
    config = load_config()
    db_client = load_vec_db(config)
    embedding_model = load_embedding_model(config)
    return config, db_client, embedding_model


def concat_history(chat_history):
    if chat_history is None or len(chat_history) == 0:
        return "在此之前没有对话记录....."
    history = "----------\n"
    for query, answer in chat_history:
        history += f"\nUser: \n{query}\n\nAssistant:{answer}\n"
    return history


def open_ai_generate(messages, model="glm4-9b-pt", api_key="dummy", base_url="http://localhost:7100/v1", stream=False):
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.5,
        stream=True
    )
    if stream:
        return response
    else:
        return response.choices[0].message.content


def open_ai_generate_stream(messages, model="glm4-9b-pt", api_key="dummy", base_url="http://localhost:7100/v1"):
    response = open_ai_generate(messages, model=model, api_key=api_key, base_url=base_url, stream=True)
    for chunk in response:
        if chunk.choices is not None and len(chunk.choices) > 0:
            yield chunk.choices[0].delta.content

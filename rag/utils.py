

import logging
import os

from langchain_ollama import ChatOllama
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from rag.config import Config


def load_config():
    config = Config()
    return config


def load_model(config):
    model = ChatOllama(
        model=config.model,
        temperature=config.temperature,
        num_predict=config.num_predict,
    )
    return model

def load_client(config):
    client = MilvusClient(os.path.join(config.db_dir, config.db_name, "data.db"))
    return client

def load_embedding_model(config: Config):
    embedding_model_dir = config.embedding_model_dir
    embedding_model_name = config.embedding_model_name
    embedding_model_path = os.path.join(embedding_model_dir, embedding_model_name)
    embedding_model = SentenceTransformer(embedding_model_path)
    logging.info(f"Embedding model loaded successfully from {embedding_model_path}, "
                 f"dimension: {embedding_model.get_sentence_embedding_dimension()}.")
    return embedding_model

def load_everything():
    config = load_config()
    model = load_model(config)
    client = load_client(config)
    embedding_model = load_embedding_model(config)
    return config, model, client, embedding_model

def concat_history(chat_history):
    if chat_history is None or len(chat_history) == 0:
        return "在此之前没有对话记录....."
    history = "----------\n"
    for query, answer in chat_history:
        history += f"\nUser: \n{query}\n\nAssistant:{answer}\n"
    return history
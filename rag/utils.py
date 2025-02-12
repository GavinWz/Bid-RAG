

import logging
import os

from langchain_ollama import ChatOllama
from openai import OpenAI
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from vllm import LLM

from rag.config import Config


def load_config():
    config = Config()
    return config

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
    client = load_client(config)
    embedding_model = load_embedding_model(config)
    return config, client, embedding_model

def concat_history(chat_history):
    if chat_history is None or len(chat_history) == 0:
        return "在此之前没有对话记录....."
    history = "----------\n"
    for query, answer in chat_history:
        history += f"\nUser: \n{query}\n\nAssistant:{answer}\n"
    return history


def open_ai_generate(messages, model="glm4-9b-pt", api_key="dummy", base_url="http://localhost:7100/v1", stream=True):
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.5,
        stream=True
    )
    if stream:
        for chunk in response:
            if chunk.choices is not None and len(chunk.choices) > 0:
                yield chunk.choices[0].delta.content
    else:
        return response.choices[0].message.content
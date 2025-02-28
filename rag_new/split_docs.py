import hashlib
import json
import logging
import re
from typing import List, Dict

from langchain_core.documents import Document
from pymilvus import MilvusClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_milvus.retrievers import MilvusCollectionHybridSearchRetriever
from langchain_milvus.utils.sparse import BM25SparseEmbedding
import os
from sentence_transformers import SentenceTransformer
from rag_new.utils import load_embedding_model
from tqdm import tqdm
from rag_new.config import Config
from rag_new.utils import load_vec_db, load_embedding_model

from elasticsearch import Elasticsearch
from langchain_community.retrievers import ElasticSearchBM25Retriever

# os.chdir(os.path.dirname(os.path.abspath(__file__)))


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# 读取文档
def read_docs(config: Config) -> List[Document]:
    '''
    读取指定目录下的所有txt文件，并返回一个包含所有文档的列表
    :param config: 配置文件
    :return: 包含所有文档的列表
    '''
    vectorized_docs_path = os.path.join(config.data_dir, "vectorized_docs.txt")
    vectorized_docs = set(load_vectorized_docs(vectorized_docs_path))

    docs = []
    input_dir = config.data_dir
    for root, dirs, files in os.walk(input_dir):
        for file_name in files:
            if file_name.endswith(".txt"):  # 只处理txt文件
                if file_name in vectorized_docs or file_name == 'vectorized_docs.txt':
                    logging.info(f"File {file_name} already exists in Milvus, skipping.")
                    continue
                else:
                    vectorized_docs.add(file_name)
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8") as f:
                    result = re.search(r'^([0-9]+\-)+(.*).txt$', file_name)
                    file_name = result[2]
                    content = f.read()
                    # 如果没有内容就跳过
                    if len(content.strip()) == 0:
                        logging.info(f"{file_name} is empty, skipped.")
                        continue
                    doc = Document(
                        page_content=content,
                        metadata={"doc_name": file_name}
                    )
                    docs.append(doc)
    logging.info(f"Loaded {len(docs)} documents from {input_dir}.")

    with open(vectorized_docs_path, 'w') as f:
        json.dump(list(vectorized_docs), f, ensure_ascii=False)
    return docs


def doc_split(docs: List[Document], config: Config) -> List[Document]:
    '''
    文档分割
    '''
    # 创建分块器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,  # 每个分块尽量最大长度
        chunk_overlap=config.chunk_overlap,  # 分块之间有一定重叠，帮助上下文衔接
        separators=["\n\n", "\n", "。", "，", " "]  # 按从大到小的优先级拆分
    )
    logging.info(f"Text splitter created.")

    # 分割文档
    splited_docs = text_splitter.split_documents(docs)

    # 为每个chunk加上chunk id
    cur_doc = ''
    cur_idx = 0
    for doc in splited_docs:
        if doc.metadata['doc_name'] != cur_doc:
            cur_doc = doc.metadata['doc_name']
            doc.metadata['chunk_id'] = 0
            cur_idx = 1
        else:
            doc.metadata['chunk_id'] = cur_idx
            cur_idx += 1
        doc.page_content = f"{doc.metadata['doc_name']} (第{doc.metadata['chunk_id']+1}段): \n\n{doc.page_content}"
    logging.info(f"{len(splited_docs)} documents splited.")
    return splited_docs


def load_vectorized_docs(file_path):
    # 定义哈希函数，用于避免添加重复向量
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            vectorized_docs = set(json.load(f))
            logging.info(f"Loaded hash set from {file_path}.")
    else:
        vectorized_docs = set()
        logging.info(f"Created new hash set.")
    return vectorized_docs


def initialize():
    '''
    最初的初始化，将政策文件夹中的所有文件添加到向量库中
    '''
    config = Config()

    # ========== 1. 读取文档 ==========
    docs = read_docs(config)

    # # ========== 2. 文档切分 ==========
    splited_docs = doc_split(docs, config)
    #
    # ========== 3. 创建/加载稠密向量数据库 ==========
    logging.info(f"Inserting into vector db ...")
    dense_embedding_model = load_embedding_model(config)
    db = load_vec_db(config, dense_embedding_model)
    db.add_documents(documents=splited_docs, verbose=True)
    logging.info(f"Completed.")

    # ========== 4. 创建/加载稀疏向量数据库 ==========
    # 初始化 ES 客户端
    elasticsearch_url = "http://localhost:9200"
    es_client = Elasticsearch(
        hosts=elasticsearch_url,
        verify_certs=False
    )

    retriever = ElasticSearchBM25Retriever.create(elasticsearch_url, config.es_index_name)
    retriever.add_texts(doc.page_content for doc in splited_docs)


def clear_db():
    config = Config()
    from pymilvus import connections, utility

    # 加载Milvus向量数据库
    # 连接到 Milvus 实例
    connections.connect(alias="default", host='localhost', port='19530')

    # 删除collection
    if utility.has_collection(config.collection_name):
        utility.drop_collection(config.collection_name)
        print(f"集合 '{config.collection_name}' 已成功删除。")
    else:
        print(f"集合 '{config.collection_name}' 不存在。")
    # 删除文档
    os.remove(os.path.join(config.data_dir, "vectorized_docs.txt"))

    # 删除稀疏向量库
    elasticsearch_url = "http://localhost:9200"
    es_client = Elasticsearch(
        hosts=elasticsearch_url,
        verify_certs=False
    )
    index_name = config.es_index_name
    if es_client.indices.exists(index=index_name):
        es_client.indices.delete(index=index_name)
        print(f"索引 {index_name} 已删除")
    else:
        print(f"索引 {index_name} 不存在")

if __name__ == '__main__':
    clear_db()
    initialize()

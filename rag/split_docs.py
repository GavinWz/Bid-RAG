import hashlib
import json
import logging
import re
from typing import List, Dict
from pymilvus import MilvusClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from sentence_transformers import SentenceTransformer
from rag.utils import load_embedding_model
from tqdm import tqdm
from rag.config import Config 

# os.chdir(os.path.dirname(os.path.abspath(__file__)))


logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 读取文档
def read_docs(config: Config) -> List[Dict]:
    '''
    读取指定目录下的所有txt文件，并返回一个包含所有文档的列表
    :param config: 配置文件
    :return: 包含所有文档的列表
    '''
    hash_file = f"{config.db_dir}/{config.db_name}/{config.collection_name}_hash"
    hash_set = load_hash_set(hash_file)

    docs = []
    input_dir = config.data_dir
    for root, dirs, files in os.walk(input_dir):
        for file_name in files:
            if file_name.endswith(".txt"):  # 只处理txt文件
                file_hash = get_string_hash(file_name)
                if file_hash in hash_set:
                    logging.info(f"File {file_name} already exists in Milvus, skipping.")
                    continue
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8") as f:
                    result = re.search(r'^([0-9]+\-)+(.*).txt$', file_name)
                    file_name = result[2] 
                    docs.append({
                        "doc_name": file_name,
                        "content": f.read()
                    })
    logging.info(f"Loaded {len(docs)} documents from {input_dir}.")

    os.makedirs(f"{config.db_dir}/{config.db_name}", exist_ok=True)
    with open(hash_file, 'w') as f:
        f.write(str(hash_set))
    return docs

def create_splitter(config: Config) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,  # 每个分块尽量最大长度
        chunk_overlap=config.chunk_overlap,  # 分块之间有一定重叠，帮助上下文衔接
        separators=["\n\n", "\n", "。", "，", " "]  # 按从大到小的优先级拆分
    )

def doc_split(docs: List[Dict], config: Config) -> List[Dict]:

    all_chunks = []
    # 创建分块器
    text_splitter = create_splitter(config)
    logging.info(f"Text splitter created.")
    for doc in docs:
        # 如果没有内容就跳过
        if len(doc['content'].strip()) == 0:
            logging.info(f"{doc['doc_name']} is empty, skipped.")
            continue
        # 分块
        chunks = text_splitter.split_text(doc['content'])
        # 可以额外存储：每个块所属文档的 ID、段落索引等信息，便于后续溯源
        for c_i, chunk in enumerate(chunks):
            all_chunks.append({
                "doc_name": doc['doc_name'],  # 文档名
                "chunk_idx": c_i,  # 段落索引
                "content": "\n\n" + doc['doc_name'] + f"(第{c_i + 1}段): \n\n" + chunk  # 段落内容
            })

    logging.info("All docs split into chunks.")
    return all_chunks

def vectorize(all_chunks, embedding_model):
    # ========== 4. 向量化 ==========
    for i in tqdm(range(len(all_chunks)), desc="Embedding chunks..."):
        item = all_chunks[i]
        content = item["content"]
        embedding = embedding_model.encode(content, show_progress_bar=False)  # 得到一个向量
        all_chunks[i]['vector'] = embedding

    # 输出 embedding 的形状
    logging.info(f"Embeded {len(all_chunks)} chunks.")


def create_vector_db(config: Config, dimension):
    db_dir = config.db_dir
    db_name = config.db_name
    collection_name = config.collection_name
    # ========== 5. 在 Milvus Lite 中创建表并插入向量 ==========
    # 创建 Milvus Lite 客户端，指定本地数据库文件路径
    os.makedirs(db_dir, exist_ok=True)
    client = MilvusClient(os.path.join(db_dir, db_name, f'data.db'))
    logging.info(f"Milvus Lite client created successfully, db path: {os.path.join(db_dir, db_name)}.")
    # 创建 Collection
    if not client.has_collection(collection_name):
        client.create_collection(
            collection_name=collection_name,
            dimension=dimension,
            primary_field="id",  # 设置主键字段名称
            auto_id=True,  # 自动生成 ID
            description="Auto-increment primary key."
        )
        logging.info(f"Collection '{collection_name}' created successfully!")
    else:
        logging.info(f"Collection '{collection_name}' already exists!")
    return client

def load_hash_set(hash_file):
    # 定义哈希函数，用于避免添加重复向量
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            hash_set = set(json.load(f))
            logging.info(f"Loaded hash set from {hash_file}.")
    else:
        hash_set = set()
        logging.info(f"Created new hash set.")
    return hash_set

# def get_vector_hash(vector):
#     vector_bytes = bytes(vector)
#     return hashlib.md5(vector_bytes).hexdigest()

def get_string_hash(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def insert_vector_to_db(all_chunks, client, config: Config):

    collection_name=config.collection_name
    # 插入向量数据, 同时更新向量哈希表，避免添加重复数据
    hash_file = f"{config.db_dir}/{collection_name}_hash"
    hash_set = load_hash_set(hash_file)
    data = []
    for i in tqdm(range(len(all_chunks)), desc="Inserting chunks..."):
        data.append({
            "id": i,
            "doc_name": all_chunks[i]['doc_name'],
            "chunk_idx": all_chunks[i]['chunk_idx'],
            "vector": all_chunks[i]['vector'],
            "content": all_chunks[i]['content']
        })
        hash = get_string_hash(all_chunks[i]['doc_name'])
        hash_set.add(hash)

    insert_results = client.insert(
        collection_name=collection_name,
        data=data
    )
    logging.info(f"Inserted {insert_results['insert_count']} vectors into '{collection_name}'.")

    # 保存哈希表
    with open(hash_file, 'w') as f:
        json.dump(list(hash_set), f)
    logging.info(f"Hash set of loaded files saved to {hash_file}.")


def index_create(client, config: Config):
    collection_name = config.collection_name
    # 创建索引参数对象
    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(
        field_name="vector",  # 向量字段名称
        index_type="HNSW",  # 索引类型
        index_name="ivf_flat_index",  # 索引名称
        metric_type="COSINE"
    )

    # 创建索引
    client.create_index(
        collection_name=collection_name,  # 指定集合名称
        index_params=index_params
    )
    logging.info(f"Index created for collection '{collection_name}'.")

if __name__ == '__main__':
    config = Config()

    # ========== 1. 读取文档 ==========
    docs = read_docs(config)

    # ========== 2. 文档切分 ==========
    all_chunks = doc_split(docs, config)

    # ========== 3. 创建向量数据库 ==========
    embedding_model = load_embedding_model(config)
    dimension = embedding_model.get_sentence_embedding_dimension()
    create_vector_db(config, dimension)

    # ========== 3. 向量化 ==========
    vectorize(all_chunks, embedding_model)

    # ========== 4. 插入向量到数据库 ==========
    client = MilvusClient(os.path.join(config.db_dir, config.db_name))
    insert_vector_to_db(all_chunks, client, config)

    # ========== 5. 创建索引 ==========
    index_create(client, config)



import hashlib
import json
from typing import List, Dict
from pymilvus import MilvusClient

from langchain.text_splitter import RecursiveCharacterTextSplitter

import os
from sentence_transformers import SentenceTransformer

import re

# ========== 1. 准备原始文本数据 ==========
# 这里我们使用一些任意文本来进行演示。实际项目中可以是采购流程文档、企业公告、FAQ 等。
raw_texts = [
    """数字化采购是通过现代信息技术和互联网平台，实现企业在采购过程中的信息共享与自动化。
       它能够帮助企业降低成本，提高效率，并优化供应链管理。""",
    """在企业数字化采购平台上，供应商可以通过在线报价、电子招标等方式与采购方进行对接。
       同时，采购方能够实时监控供应商资质，跟踪合同执行情况，减少人工操作失误。""",
    """常见的采购流程包括需求确认、供应商筛选、询价与比价、合同签订、订单执行与对账等步骤。
       数字化采购能够为其中的每个环节提供数据和系统支撑，从而提升整个采购流程的透明度。"""
]


# ========== 2. 文档分块 ==========
# 为了便于检索，我们通常需要将长文本分块，避免单段过长导致 embedding 效果下降。
# 这里以一个简化的分块方法为例，按字符数切分，也可以按句子或 token 切分。
# 初始化一个文本分割器
def doc_split(raw_texts: List[str]) -> List[Dict]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,  # 每个分块尽量不超过50字符
        chunk_overlap=10,  # 分块之间有一定重叠，帮助上下文衔接
        separators=["\n\n", "\n", "。", "，", " "]  # 按从大到小的优先级拆分
    )

    all_chunks = []
    for idx, txt in enumerate(raw_texts):
        # 去除多余换行、空白
        cleaned_txt = re.sub(r"\s+", " ", txt).strip()
        # 分块
        chunks = text_splitter.split_text(cleaned_txt)
        # 可以额外存储：每个块所属文档的 ID、段落索引等信息，便于后续溯源
        for c_i, chunk in enumerate(chunks):
            all_chunks.append({
                "doc_id": idx,
                "chunk_index": c_i,
                "content": chunk
            })

    # print("分块结果示例：")
    # for item in all_chunks:
    #     print(f"(Doc {item['doc_id']}, Chunk {item['chunk_index']}): {item['content']}")

    return all_chunks


# testing code
all_chunks = doc_split(raw_texts)
print(all_chunks)

# ========== 3. 选择与加载 Embedding 模型 ==========
# 这里选用 sentence-transformers 提供的多语言模型做简单演示
# （如果是中文环境，也可以根据需要选择中文专用模型，例如 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2' 等）
embedding_model_dir = '/root/models/embedding_models'
# embedding_model_name = 'paraphrase-multilingual-MiniLM-L12-v2'  # 384维
# embedding_model_name = 'conan-embedding-v1'   # 1792维
embedding_model_name = 'distiluse-base-multilingual-cased-v2'  # 512维
embedding_model_path = os.path.join(embedding_model_dir, embedding_model_name)
embedding_model = SentenceTransformer(embedding_model_path)

# ========== 4. 向量化 ==========
for i in range(len(all_chunks)):
    item = all_chunks[i]
    content = item["content"]
    embedding = embedding_model.encode(content)  # 得到一个向量
    all_chunks[i]['vector'] = embedding

# 输出 embedding 的形状
print(f"示例 embedding 维度：{len(all_chunks[0]['vector'])}")


# ========== 5. 在 Milvus Lite 中创建表并插入向量 ==========
# 创建 Milvus Lite 客户端，指定本地数据库文件路径
db_dir = '../vec_dbs'
db_name = "milvus_demo.db"
client = MilvusClient(os.path.join(db_dir, db_name))

# 创建 Collection
collection_name = "demo_knowledge_base"
dimension = len(all_chunks[0]['vector'])  # 向量的维度（由 embedding 模型决定）

if not client.has_collection(collection_name):
    client.create_collection(
        collection_name=collection_name,
        dimension=dimension,
        primary_field="id",  # 设置主键字段名称
        auto_id=True,  # 自动生成 ID
        description="Knowledge base for text chunks"
    )
    print(f"Collection '{collection_name}' created successfully!")
else:
    print(f"Collection '{collection_name}' already exists!")


# 定义哈希函数，用于避免添加重复向量
hash_file = f"../vec_dbs/{collection_name}_hash"
if os.path.exists(hash_file):
    hash_set = set(json.load(open(hash_file, 'r')))
else:
    hash_set = set()

def get_vector_hash(vector):
    vector_bytes = bytes(vector)
    return hashlib.md5(vector_bytes).hexdigest()

# 插入向量数据, 同时更新向量哈希表，避免添加重复数据
data = []
for i in range(len(all_chunks)):
    hash = get_vector_hash(all_chunks[i]['vector'])
    if hash not in hash_set:
        data.append({
            "id": i,
            "doc_id": all_chunks[i]['doc_id'],
            "chunk_index": all_chunks[i]['chunk_index'],
            "vector": all_chunks[i]['vector'],
            "content": all_chunks[i]['content'],
            "subject": "history"
        })
        hash_set.add(hash)
json.dump(list(hash_set), open(hash_file, 'w'))

insert_results = client.insert(
    collection_name=collection_name,
    data=data
)
print(f"Inserted {len(insert_results)} vectors into '{collection_name}'.")

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
print(f"Index created for collection '{collection_name}'.")

# 加载 Collection
client.load_collection(collection_name)

# ========== 6. 简单检索示例 (可选) ==========
# 现在我们可以对这个向量数据库做一个简单的相似度搜索
# 比如我们想问： "数字化采购能带来哪些好处？"

query_text = "数字化采购能带来哪些好处？"
query_emb = embedding_model.encode(query_text).tolist()

search_params = {
    "metric_type": "COSINE",  # Inner Product
    "params": {"nprobe": 256}
}

# collection.search 接口需要按 [query_emb] 这样写成二维
results = client.search(
    collection_name=collection_name,  # 指定集合名称
    data=[query_emb],  # 查询向量
    anns_field="vector",  # 向量字段名称
    search_params=search_params,  # 检索参数
    limit=3,  # 返回前 3 个结果
    output_fields=["doc_id", "chunk_index", "content"]  # 返回字段
)

print("\n检索结果：")
for i, hits in enumerate(results):
    print(f"\n对第 {i + 1} 条查询结果：")
    for hit in hits:
        score = hit['distance']
        result_doc_id = hit['entity'].get("doc_id")
        result_chunk_index = hit['entity'].get("chunk_index")
        result_content = hit['entity'].get("content")
        print(
            f"  -> doc_id:{result_doc_id}, chunk_index:{result_chunk_index}, score:{score:.4f}, content:{result_content}")

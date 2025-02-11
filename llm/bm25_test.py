from rank_bm25 import BM25Okapi
import jieba  # 用于中文分词

# 示例文档集合
documents = [
    "BM25是一种用于信息检索的排名算法。",
    "它广泛应用于搜索引擎和文档检索系统。",
    "BM25通过计算查询词项与文档的匹配程度来评估相关性。"
]

# 分词
tokenized_docs = [list(jieba.cut(doc)) for doc in documents]

# 构建BM25模型
bm25 = BM25Okapi(tokenized_docs)

# 示例查询
query = "BM25算法如何应用于信息检索？"
tokenized_query = list(jieba.cut(query))

# 计算BM25得分
doc_scores = bm25.get_scores(tokenized_query)

# 排序并返回相关文档
import numpy as np
top_k = 2
top_k_indices = np.argsort(doc_scores)[::-1][:top_k]

for idx in top_k_indices:
    print(f"Document: {documents[idx]}, Score: {doc_scores[idx]}")
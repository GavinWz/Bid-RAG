import hnswlib
import numpy as np
from transformers import RagTokenizer, RagRetriever, RagSequenceForGeneration

# 1. 准备数据
# 假设我们有一组文档嵌入（embedding）和对应的文本
doc_embeddings = np.random.rand(1000, 768).astype('float32')  # 1000个文档，每个文档的embedding维度为768
doc_texts = [f"Document {i}" for i in range(1000)]  # 对应的文档文本

# 2. 构建HNSW索引
dim = 768  # 嵌入维度
num_elements = len(doc_embeddings)  # 文档数量

# 创建HNSW索引
hnsw_index = hnswlib.Index(space='cosine', dim=dim)
hnsw_index.init_index(max_elements=num_elements, ef_construction=200, M=16)
hnsw_index.add_items(doc_embeddings)

# 设置查询时的参数
hnsw_index.set_ef(50)

# 3. 检索相关文档
query_embedding = np.random.rand(1, 768).astype('float32')  # 假设我们有一个查询的embedding
k = 5  # 检索最相关的5个文档

# 使用HNSW进行最近邻搜索
labels, distances = hnsw_index.knn_query(query_embedding, k=k)

# 获取检索到的文档文本
retrieved_docs = [doc_texts[label] for label in labels[0]]
print("Retrieved Documents:", retrieved_docs)
#=======================================================================
# 4. 结合RAG模型进行生成
# 加载RAG模型和tokenizer
tokenizer = RagTokenizer.from_pretrained("facebook/rag-sequence-nq")
retriever = RagRetriever.from_pretrained("facebook/rag-sequence-nq", index_name="custom", passages=doc_texts, embeddings=doc_embeddings)
model = RagSequenceForGeneration.from_pretrained("facebook/rag-sequence-nq", retriever=retriever)

# 假设我们有一个查询文本
query_text = "What is the capital of France?"

# 使用RAG模型生成答案
input_ids = tokenizer(query_text, return_tensors="pt").input_ids
generated_ids = model.generate(input_ids)
generated_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

print("Generated Answer:", generated_text)
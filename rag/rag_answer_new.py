from rag.utils import concat_history

class RagModule():
    def __init__(self, config, model, client, embedding_model):
        self.config = config
        self.model = model
        self.client = client
        self.embedding_model = embedding_model

    def recall(self, query_text, mute=False):
        # 加载 Collection
        self.client.load_collection(self.config.collection_name)

        query_emb = self.embedding_model.encode(query_text).tolist()

        search_params = {
            "metric_type": "COSINE",  # Inner Product
            "params": {"nprobe": 256}
        }

        # collection.search 接口需要按 [query_emb] 这样写成二维
        results = self.client.search(
            collection_name=self.config.collection_name,  # 指定集合名称
            data=[query_emb],  # 查询向量
            anns_field="vector",  # 向量字段名称
            search_params=search_params,  # 检索参数
            limit=self.config.topk,  # 返回前 k 个结果
            output_fields=["doc_name", "chunk_idx", "content"]  # 返回字段
        )
        if not mute:
            print("\n检索结果：")
        knowledge = []
        for _, hits in enumerate(results):
            for hit in hits:
                score = hit['distance']
                if score < self.config.recall_threshold:
                    break
                result_doc_name = hit['entity'].get("doc_name")
                result_chunk_idx = hit['entity'].get("chunk_idx")
                result_content = hit['entity'].get("content")
                knowledge.append((result_content))
                if not mute:
                    print(f"  -> doc_name:{result_doc_name}, chunk_idx:{result_chunk_idx}, "
                        f"score:{score:.4f}, content:{result_content}")
        if len(knowledge) == 0:
            print("  -> 没有找到相关文档。")
        return knowledge


    def answer_with_rag(self, query_text, stream=False):
        knowledge = self.recall(query_text, mute=True)
        print(knowledge)
        if len(knowledge) == 0:
            prompt = query_text
        else:
            background = '\n'.join(knowledge)
            prompt = f'''
            根据背景信息回答问题，背景信息可能会涉及多个方面，包括但不限于：商业招投标，采购，企业管理，政府政策，法律条文，商品信息，企业概况，舆情信息等等。

            "背景信息"：
            """
            {background}
            """

            请结合以上"背景信息"，准确地回答问题。如果你觉得相关背景信息和用户的提问并不相关，则直接忽略背景信息，根据你自己的判断来回答。
            
            "问题"：
            """
            {query_text}
            """
            '''

        # 调用模型生成回复
        if stream:
            response_chunks = self.model.stream(prompt)
            return response_chunks
        else:
            response = self.model.invoke(prompt)
            return response.content

    
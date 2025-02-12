import math
import os
import re

import pandas as pd

from rag.config import Config
from rag.eval.eval_data import create_vec_db
from rag.rag_answer import RagModule
from rag.utils import load_client, load_embedding_model, load_everything, load_model


def mrr_and_recall(all_results, all_questions):
    n = 0
    total = 0
    success = 0
    for i in range(len(all_results)):
        results = all_results[i]
        questions = all_questions[i]
        true_doc_name = questions['doc_name']
        true_chunk_id = questions['chunk_id']
        for result in results:
            n += 1
            rank = 1
            for item in result:
                if item['entity']['doc_name'] == true_doc_name and item['entity']['chunk_idx'] == true_chunk_id:
                    total += 1 / rank
                    success += 1
                    break
                else:
                    rank += 1
    return total / n, success / n


def eval(embedding_model_name):
    config = Config(
        config_file=None,
        model="glm4-9b",
        temperature=0.8,
        num_predict=2048,
        embedding_model_dir='/root/models/embedding_models',
        embedding_model_name=embedding_model_name,  # 512维
        data_dir='data',
        db_dir='./vec_dbs',
        db_name=embedding_model_name,
        collection_name="policy",
        chunk_size=4096,
        chunk_overlap=1000,
        recall_threshold=0.2,
        topk=30
    )

    embedding_model = load_embedding_model(config)

    if not os.path.exists(os.path.join(config.db_dir, config.db_name)):
        client = create_vec_db(config)
    else:
        client = load_client(config)

    client.load_collection(config.collection_name)

    df = pd.read_excel("eval_data.xlsx")

    all_results = []
    all_questions = []

    for row in df.itertuples(index=True, name='Row'):
        doc_name = row.doc_name
        chunk_idx = row.chunk_idx
        if str(row.questions) == 'nan':
            continue
        raw_questions = row.questions.strip()
        questions = re.split(r'\n+', raw_questions)
        # questions = [f"结合{doc_name}: \n" + question for question in questions]

        query_emb = embedding_model.encode(questions).tolist()

        search_params = {
            "metric_type": "COSINE",  # Inner Product
            "params": {
                "nprobe": 256,
                "radius": config.recall_threshold
            }
        }

        # collection.search 接口需要按 [query_emb] 这样写成二维
        results = client.search(
            collection_name=config.collection_name,  # 指定集合名称
            data=query_emb,  # 查询向量
            anns_field="vector",  # 向量字段名称
            search_params=search_params,  # 检索参数
            limit=config.topk,  # 返回前 k 个结果
            output_fields=["doc_name", "chunk_idx"]  # 返回字段
        )

        # print(results)
        item = {
            'doc_name': doc_name,
            'chunk_id': chunk_idx,
            'questions': questions
        }
        all_questions.append(item)
        all_results.append(results)

    with open(f'results/{embedding_model_name}', 'w') as f:
        f.write(str(mrr_and_recall(all_results, all_questions)))


if __name__ == '__main__':
    # eval("distiluse-base-multilingual-cased-v2")
    # eval("xiaobu-embedding-v2")
    eval("Conan-embedding-v1")

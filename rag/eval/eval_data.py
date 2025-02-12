import time

from openai import OpenAI

from rag.split_docs import *
from rag.utils import load_embedding_model, load_client
import json
import pandas as pd

def create_vec_db(config):
    # ========== 1. 读取文档 ==========
    docs = read_docs(config)

    # ========== 2. 文档切分 ==========
    all_chunks = doc_split(docs, config)[:200]

    # ========== 3. 创建向量数据库 ==========
    embedding_model = load_embedding_model(config)
    dimension = embedding_model.get_sentence_embedding_dimension()
    create_vector_db(config, dimension)

    # ========== 3. 向量化 ==========
    vectorize(all_chunks, embedding_model)

    # ========== 4. 插入向量到数据库 ==========
    client = MilvusClient(os.path.join(config.db_dir, config.db_name, 'data.db'))
    insert_vector_to_db(all_chunks, client, config)

    # ========== 5. 创建索引 ==========
    index_create(client, config)
    return client

def generate_questions(text_content, client, model):
    prompt1 = '''
    你是一个阅读理解题目设计专家，你擅长根据我提供的一段文字设计相关的问题。
    我提供的文字可能会涉及多个方面，包括但不限于：商业招投标，采购，企业管理，政府政策，法律条文，商品信息，企业概况，舆情信息等等。

    以下是我给出的文本：

    """

    {{此处替换成你的内容}}

    """

    结合文本设计问题，以下是具体的问题设计要求：
    1. 问题要尽量短，不要太长。

    2. 避免使用“本”、“该”、“其”、“此”、“这个”等代词，将问题中的代词替换为原文中对应实体的全称。

    3. 对文章中提到的专有名词，使用它的全称代替缩写，比如：
    原文中提到：“《合肥市涉密项目交易操作办法（试行）》（以下简称“办法”）”
    那么，在生成的问题中，使用《合肥市涉密项目交易操作办法（试行）》，不要使用《办法》。

    4. 生成的问题必须宏观、有价值，不要生成特别细节的问题。

    5. 一句话包含一个问题，多个问题之间必须使用换行符分隔。回答示例：

    """

    投标人或其他利害管理人对评标结果有异议应当如何处理？\n  

    中标人是否可对中标项目进行分包、转包？\n  

    合肥市涉密项目交易管理面临的主要挑战是什么？\n  

    """

    5. 不要生成任何的HTML标签

    '''

    prompt = prompt1.replace("{{此处替换成你的内容}}", text_content)
    messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": prompt}
    ]
    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False
    )
    return response.choices[0].message.content

def question_gen(data):
    # 替换为您自己的DeepSeek API密钥
    api_key = 'sk-GTJJepLkpBjc3a3752B117049fEc489f9c63F8944cDdA0Ec'
    client = OpenAI(api_key=api_key, base_url="https://openai.sohoyo.io/v1/")
    model = "gpt-4o"
    for item in data:
        questions = generate_questions(item['content'], client, model)
        item['questions'] = questions


    # # 替换为您自己的DeepSeek API密钥
    # api_key = 'sk-Jz6bVV1X8W0By9UYCVvasM3rZTzEqtB2LktxDetpXdqtDZBZ'
    # client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")

    # model = "moonshot-v1-8k"

    # # ollama
    # from langchain_ollama import OllamaLLM
    # model = OllamaLLM(model="glm4-9b")


if __name__ == '__main__':
    config = Config(
        config_file=None,
        model="glm4-9b",
        temperature=0.8,
        num_predict=2048,
        embedding_model_dir='/root/models/embedding_models',
        embedding_model_name='distiluse-base-multilingual-cased-v2',  # 512维
        data_dir='data',
        db_dir='.',
        db_name="bid_rag.db",
        collection_name="policy",
        chunk_size=4096,
        chunk_overlap=1000,
        recall_threshold=0.2,
        topk=3
    )
    # create_vec_db(config)
    client = load_client(config)
    result = client.query(
        collection_name=config.collection_name,  # 指定集合名称
        limit=10000,
        output_fields=["doc_name", "chunk_idx", "content"]  # 返回字段
    )

    question_gen(result)
    df = pd.DataFrame(result)
    df.to_excel("eval_data.xlsx")
    print(df)





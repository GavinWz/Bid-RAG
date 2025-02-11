import torch

# 检查是否有可用的GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)

import pandas as pd
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import SentenceTransformer
from rouge import Rouge
import time

models = [
    # "glm4-9b",
    "AQwen2.5-7B",
]

output_parser = StrOutputParser()

for model_name in models:
    # 创建一个列表来存储当前模型的问答结果
    results = []

    # 创建模型实例
    llm = ChatOllama(
        model=model_name,
        temperature=0,
        # other params...
    )

    start_time = time.time()
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个乐于解答各种问题的助手，你的任务是为用户提供专业、准确、有见地的建议。"),
        ("user", "{input}")
    ])
    
    # 创建链
    chain = prompt | llm | output_parser

    # 调用链并获取回答
    response = chain.invoke({"input": "帮我制定一份健身计划"})

    print(f"总计用时：{time.time - start_time}秒")
    print(response)

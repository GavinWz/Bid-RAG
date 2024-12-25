import pandas as pd
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 定义问题和模型列表
df = pd.read_excel('问题答案样例数据0113.xlsx', sheet_name='Sheet1')

# 提取问题列并转换为列表
questions = df['问'].tolist()

models = [
    # "Qwen2.5:7B",
    "Llama3.2:3B",
    # "glm4:9B",
    # 添加更多模型...
]

output_parser = StrOutputParser()

for model_name in models:
    # 创建一个列表来存储当前模型的问答结果
    data = []

    # 创建模型实例
    llm = ChatOllama(
        model=model_name,
        temperature=0,
        # other params...
    )

    for question in questions:
        try:
            # 创建提示模板
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个乐于解答各种问题的助手，你的任务是为用户提供专业、准确、有见地的建议。"),
                ("user", "{input}")
            ])
            # 创建链
            chain = prompt | llm | output_parser

            # 调用链并获取回答
            response = chain.invoke({"input": question})

            # 将问答结果添加到列表
            data.append({'Question': question, 'Answer': response})
        except Exception as e:
            print(f"模型 {model_name} 在处理问题 '{question}' 时出错: {e}")

    # 将列表转换为DataFrame
    df = pd.DataFrame(data)

    # 将当前模型的问答结果保存到单独的Excel文件中
    excel_filename = f"{model_name.replace(':', '_')}_responses.xlsx"
    df.to_excel(excel_filename, index=False)
    print(f"模型 {model_name} 的问答结果已保存到 {excel_filename}")

print("所有模型的问答结果已保存到各自的Excel文件中")

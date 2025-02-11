import pandas as pd
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import SentenceTransformer, util
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge import Rouge
import time
import jieba
import re

# 初始化向量模型
embedding_model = SentenceTransformer('/root/models/embedding_models/distiluse-base-multilingual-cased-v2')

# 定义问题和模型列表
df = pd.read_excel('/root/rag_project/data/问答对/问题答案test.xlsx', sheet_name='Sheet1')
# df = pd.read_excel('/root/rag_project/data/问答对/问题答案样例数据.xlsx', sheet_name='Sheet1')

# 提取问题列并转换为列表
questions = df['问'].tolist()
reference_answers = df['答'].tolist()

models = [
    # "glm4-9b",
    "AQwen2.5-7B",
]

output_parser = StrOutputParser()

# 初始化ROUGE评估器
rouge = Rouge()

for model_name in models:
    # 创建一个列表来存储当前模型的问答结果
    results = []

    # 创建模型实例
    llm = ChatOllama(
        model=model_name,
        temperature=0,
        # other params...
    )

    for i, (question, reference_answer) in enumerate(zip(questions, reference_answers), start=1):
        try:
            start_time = time.time()
            # 创建提示模板
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个乐于解答各种问题的助手，你的任务是为用户提供专业、准确、有见地的建议。"),
                ("user", "{input}")
            ])
            # 创建链
            chain = prompt | llm | output_parser

            # 调用链并获取回答
            response = chain.invoke({"input": question})

            # 计算句子的嵌入
            embedding1 = embedding_model.encode(reference_answer, convert_to_tensor=True)
            embedding2 = embedding_model.encode(response, convert_to_tensor=True)
            print("embedding1:", embedding1)
            print("embedding2:", embedding2)
            # 计算余弦相似度
            similarity_score = util.pytorch_cos_sim(embedding1, embedding2).item()
            print("similarity_score:", similarity_score)

            # 分词
            # reference_answer_list = re.findall(r'.', reference_answer)
            # anwser_list = re.findall(r'.', response)
            reference_answer_list = jieba.lcut(reference_answer)
            anwser_list = jieba.lcut(response)

            # 使用平滑函数避免分数为 0
            smoother = SmoothingFunction().method1

            # 计算 BLEU 分数   precision_1, precision_2, precision_3, precision_4
            bleu_score = sentence_bleu(
                reference_answer_list,  # 参考文本（分词后的列表）
                anwser_list,    # 生成文本（分词后的列表）
                weights=(0.25, 0.25, 0.25, 0.25),  # 1-gram 到 4-gram 的权重
                smoothing_function=smoother  # 使用平滑函数
            )

            # 计算ROUGE分数
            rouge_scores = rouge.get_scores(response, reference_answer)[0]

            results.append({
                "Similarity": similarity_score,
                "BLEU": bleu_score,
                "ROUGE-1": rouge_scores['rouge-1']['r'],
                "ROUGE-2": rouge_scores['rouge-2']['r'],
                "ROUGE-L": rouge_scores['rouge-l']['r'],
                "Question": question,
                "Answer": response,
                "Reference_answer": reference_answer
            })

            print(f"第{i}个问题回答完毕,耗时{time.time() - start_time}秒")

        except Exception as e:
            print(f"模型 {model_name} 在处理问题 '{question}' 时出错: {e}")

    # 计算平均相似度、BLEU和ROUGE分数
    average_similarity = sum(result["Similarity"] for result in results) / len(results)
    average_bleu = sum(result["BLEU"] for result in results) / len(results)
    average_rouge1 = sum(result["ROUGE-1"] for result in results) / len(results)
    average_rouge2 = sum(result["ROUGE-2"] for result in results) / len(results)
    average_rougeL = sum(result["ROUGE-L"] for result in results) / len(results)

    # 将平均分数添加到结果列表中
    results.append({
        "Similarity": average_similarity,
        "BLEU": average_bleu,
        "ROUGE-1": average_rouge1,
        "ROUGE-2": average_rouge2,
        "ROUGE-L": average_rougeL,
        "Question": "",
        "Answer": "",
        "Reference_answer": ""
    })

    # 将列表转换为DataFrame
    df = pd.DataFrame(results)

    # 将当前模型的问答结果保存到单独的Excel文件中
    excel_filename = f"/root/rag_project/llm/{model_name.replace(':', '_')}_responses.xlsx"
    df.to_excel(excel_filename, index=False)
    print(f"模型 {model_name} 的问答结果已保存到 {excel_filename}")

print("所有模型的问答结果已保存到各自的Excel文件中")
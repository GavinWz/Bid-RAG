import pandas as pd
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import SentenceTransformer, util
import time
import jieba
import os
# os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
import json

# # 动态添加项目根目录到 sys.path
print(sys.path)
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.abspath(os.path.join(current_dir, ".."))
# sys.path.append(project_root)

from rag.utils import load_everything
from rag.rag_answer import RagModule
config, model, client, embedding_model = load_everything()
rag_module = RagModule(config, model, client, embedding_model)

# 初始化向量模型
embedding_model = SentenceTransformer('/dev/models/embedding_models/paraphrase-multilingual-MiniLM-L12-v2')

# 从 JSON 文件中提取问答对
def extract_qa_pairs(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions = []
    reference_answers = []
    
    for item in data:
        messages = item['messages']
        user_content = None
        assistant_content = None
        
        for message in messages:
            if message['role'] == 'user':
                user_content = message['content']
            elif message['role'] == 'assistant':
                assistant_content = message['content']
        
        if user_content and assistant_content:
            questions.append(user_content)
            reference_answers.append(assistant_content)
    
    return questions, reference_answers

# 读取 JSON 文件并提取问答对
json_file = '/root/rag_project/llm/LLaMA-Factory/data/安徽合肥公共资源交易中心-政策-outputQA-sample.json'
questions, reference_answers = extract_qa_pairs(json_file)

models = [
    "AQwen2.5-7B",
    # "glm4-9b"
]

def calculate_1gram_metrics(reference, generated):
    """计算 1-gram 的精确率、召回率和 F1 分数"""
    # 分词
    reference_tokens = set(jieba.lcut(reference))
    generated_tokens = set(jieba.lcut(generated))
    
    # 计算匹配词数
    matched_tokens = reference_tokens.intersection(generated_tokens)
    
    # 计算 1-gram 精确率和召回率
    precision = len(matched_tokens) / len(generated_tokens) if len(generated_tokens) > 0 else 0
    recall = len(matched_tokens) / len(reference_tokens) if len(reference_tokens) > 0 else 0
    
    # 计算 F1 分数
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return precision, recall, f1

def longest_common_subsequence(text1, text2):
    """计算两个文本的最长公共子序列（LCS）的长度"""
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    
    return dp[m][n]

def calculate_lcs_recall(reference, generated):
    """计算 LCS 的召回率"""
    # 分词
    reference_tokens = jieba.lcut(reference)
    generated_tokens = jieba.lcut(generated)
    
    # 计算 LCS 的长度
    lcs_length = longest_common_subsequence(reference_tokens, generated_tokens)
    
    # 计算 LCS 召回率
    recall_lcs = lcs_length / len(reference_tokens) if len(reference_tokens) > 0 else 0
    
    return recall_lcs

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
            # prompt = ChatPromptTemplate.from_messages([
            #     ("system", "你是一个乐于解答各种问题的助手，你的任务是为用户提供专业、准确、有见地的建议。"),
            #     ("user", "{input}")
            # ])
            # # 创建链
            # chain = prompt | llm | output_parser

            # # 调用链并获取回答
            # response = chain.invoke({"input": question})
            response = rag_module.answer_with_rag_once(question)
            print(f"第{i}个问题: {question}", f"回答: {response}\n")

            # 计算句子的嵌入
            embedding1 = embedding_model.encode(reference_answer, convert_to_tensor=True)
            embedding2 = embedding_model.encode(response, convert_to_tensor=True)

            # 计算余弦相似度
            similarity_score = util.pytorch_cos_sim(embedding1, embedding2).item()

            # 计算 1-gram 精确率、召回率和 F1 分数
            precision_1gram, recall_1gram, f1_1gram = calculate_1gram_metrics(reference_answer, response)

            # 计算 LCS 召回率
            recall_lcs = calculate_lcs_recall(reference_answer, response)

            results.append({
                "Similarity": similarity_score,
                "Precision": precision_1gram,
                "Recall": recall_1gram,
                "F1-score": f1_1gram,
                "LCS Recall": recall_lcs,
                "Question": question,
                "Answer": response,
                "Reference_answer": reference_answer
            })

            print(f"第{i}个问题回答完毕,耗时{time.time() - start_time}秒")

        except Exception as e:
            print(f"模型 {model_name} 在处理问题 '{question}' 时出错: {e}")

    # 计算平均相似度、1-gram 精确率、1-gram 召回率、1-gram F1 分数和 LCS 召回率
    average_similarity = sum(result["Similarity"] for result in results) / len(results)
    average_precision_1gram = sum(result["Precision"] for result in results) / len(results)
    average_recall_1gram = sum(result["Recall"] for result in results) / len(results)
    average_f1_1gram = sum(result["F1-score"] for result in results) / len(results)
    average_recall_lcs = sum(result["LCS Recall"] for result in results) / len(results)

    # 将平均分数添加到结果列表中
    results.append({
        "Similarity": average_similarity,
        "Precision": average_precision_1gram,
        "Recall": average_recall_1gram,
        "F1-score": average_f1_1gram,
        "LCS Recall": average_recall_lcs,
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
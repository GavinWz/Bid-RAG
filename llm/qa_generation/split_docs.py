import logging
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import sys
import json

# 动态添加项目根目录到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
sys.path.append(project_root)

from rag_project.rag.config import Config

def create_splitter(config: Config) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,  # 每个分块尽量最大长度
        chunk_overlap=config.chunk_overlap,  # 分块之间有一定重叠，帮助上下文衔接
        separators=["\n\n", "\n", "。", "，", " "]  # 按从大到小的优先级拆分
    )

def doc_split(docs: List[Dict], config: Config) -> List[Dict]:
    all_chunks = []
    # 创建分块器
    text_splitter = create_splitter(config)
    logging.info(f"Text splitter created.")
    for doc in docs:
        # 如果没有内容就跳过
        if len(doc['content'].strip()) == 0:
            logging.info(f"{doc['doc_name']} is empty, skipped.")
            continue
        # 分块
        chunks = text_splitter.split_text(doc['content'])
        # 可以额外存储：每个块所属文档的 ID、段落索引等信息，便于后续溯源
        for c_i, chunk in enumerate(chunks):
            all_chunks.append({
                "doc_name": doc['doc_name'],  # 文档名
                "chunk_idx": c_i,  # 段落索引
                "content": chunk  # 段落内容
            })

    logging.info("All docs split into chunks.")
    return all_chunks

def process_folder(input_folder: str, output_folder: str, config: Config):
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 遍历输入文件夹中的所有文件
    for filename in os.listdir(input_folder):
        input_file_path = os.path.join(input_folder, filename)
        output_file_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}.json")

        # 读取文件内容
        with open(input_file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # 如果文件内容为空，跳过该文件
        if len(content.strip()) == 0:
            logging.info(f"File {filename} is empty, skipped.")
            continue

        # 创建文档字典
        doc = {
            'doc_name': filename,
            'content': content
        }

        # 分块
        chunks = doc_split([doc], config)

        # 将分块内容保存为 JSON 格式
        json_data = [{"text": chunk["content"]} for chunk in chunks]

        # 将 JSON 数据写入输出文件
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            json.dump(json_data, output_file, ensure_ascii=False, indent=4)

        logging.info(f"Processed {filename} and saved to {output_file_path}")

# 示例调用
if __name__ == "__main__":
    config = Config(chunk_size=500, chunk_overlap=50)
    input_folder = "/root/rag_project/data/crawled/安徽合肥公共资源交易中心/政策"
    output_folder = "/root/rag_project/data/pretraining_chunks/安徽合肥公共资源交易中心/政策"
    process_folder(input_folder, output_folder, config)
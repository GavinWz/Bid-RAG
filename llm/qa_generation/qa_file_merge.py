import os
import json
import re

def clean_json_content(content):
    """
    清理 JSON 内容中的无效控制字符
    """
    # 使用正则表达式去除无效控制字符（\x00-\x1F 之间的字符，除了 \t, \n, \r）
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', content)

def merge_json_files(source_folder, target_folder, dataset_info_file):
    # 确保目标文件夹存在
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # 从 source_folder 中提取最后一部分作为输出文件名的基础
    base_filename = os.path.basename(source_folder)
    parent_folder_name = os.path.basename(os.path.dirname(os.path.normpath(source_folder)))
    output_filename = f"{parent_folder_name}-{base_filename}-outputQA.json"

    # 初始化一个列表来存储所有合并后的对话
    merged_data = []

    # 遍历源文件夹中的所有文件
    for filename in os.listdir(source_folder):
        if filename.endswith('.json'):
            file_path = os.path.join(source_folder, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # 清理无效控制字符
                cleaned_content = clean_json_content(content)
                try:
                    # 解析 JSON 内容
                    data = json.loads(cleaned_content)
                    # 将当前文件的对话列表合并到总列表中
                    merged_data.extend(data)
                except json.JSONDecodeError as e:
                    print(f"文件 {filename} 解析失败，错误信息: {e}")
                    continue

    # 将合并后的数据写入目标文件夹中的输出文件
    output_path = os.path.join(target_folder, output_filename)
    with open(output_path, 'w', encoding='utf-8') as output_file:
        json.dump(merged_data, output_file, ensure_ascii=False, indent=4)

    print(f"合并完成，结果已保存到 {output_path}")

    # 构建要追加到 dataset_info.json 的数据
    dataset_info = {
        f"{parent_folder_name}-{base_filename}-outputQA": {
            "file_name": output_filename,
            "formatting": "sharegpt",
            "columns": {
                "messages": "messages"
            },
            "tags": {
                "role_tag": "role",
                "content_tag": "content",
                "user_tag": "user",
                "assistant_tag": "assistant",
                "system_tag": "system"
            }
        }
    }

    # 读取现有的 dataset_info.json 文件
    if os.path.exists(dataset_info_file):
        with open(dataset_info_file, 'r', encoding='utf-8') as info_file:
            existing_data = json.load(info_file)
    else:
        existing_data = {}

    # 将新的数据集信息追加到现有数据中
    existing_data.update(dataset_info)

    # 将更新后的数据写回 dataset_info.json 文件
    with open(dataset_info_file, 'w', encoding='utf-8') as info_file:
        json.dump(existing_data, info_file, ensure_ascii=False, indent=4)

    print(f"数据集信息已追加到 {dataset_info_file}")

# 示例用法
source_folder = '/root/rag_project/data/qa/安徽合肥公共资源交易中心/政策'  # 源文件夹路径
target_folder = '/root/rag_project/llm/LLaMA-Factory/data'  # 目标文件夹路径
dataset_info_file = '/root/rag_project/llm/LLaMA-Factory/data/dataset_info.json'  # 数据集信息文件路径

merge_json_files(source_folder, target_folder, dataset_info_file)
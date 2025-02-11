import datetime
import time
import os
from openai import OpenAI

# 替换为您自己的DeepSeek API密钥
api_key = 'sk-472be1015a15453f99a0b74f39e19350'
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

model = "deepseek-chat"

prompt1 = '''
#01 你是一个问答对数据集处理专家。

#02 你的任务是根据我给出的内容，生成适合作为问答对数据集的问题。

#03 问题要尽量短，不要太长。

#04 一句话中只能有一个问题。

#05 生成的问题必须宏观、有价值，不要生成特别细节的问题。

#06 生成问题示例：

"""

中标通知书的发送对象是谁、效力如何？

依法必须进行招标的项目，招标人应于何时公示中标候选人？

"""

#07 以下是我给出的内容：

"""

{{此处替换成你的内容}}

"""
'''

prompt2 = '''
#01 你是一个问答对数据集处理专家。

#02 你的任务是根据我的问题和我给出的内容，生成对应的问答对。

#03 答案要全面，多使用我的信息，内容要更丰富。

#04 你必须根据我的问答对示例格式来生成：

"""

{
  "instruction": "中标通知书的发送对象是谁、效力如何？",
  "input": "",
  "output": "中标人确定后，招标人应当向中标人发出中标通知书，并同时将中标结果通知所有未中标的投标人。中标通知书对招标人和中标人具有法律效力。中标通知书发出后，招标人改变中标结果的，或者中标人放弃中标项目的，应当依法承担法律责任。"
}

{
  "instruction": "依法必须进行招标的项目，招标人应于何时公示中标候选人？",
  "input": "",
  "output": "招标人应当自收到评标报告之日起3日内公示中标候选人，公示期不得少于3日。"
}

#05 我的问题如下：

"""

{{此处替换成你上一步生成的问题}}

"""

#06 我的内容如下：

"""

{{此处替换成你的内容}}

"""
'''


def generate_question(text_content, more=False):
    content = "生成适合作为问答对的问题"
    if more:
        content = "尽可能多生成适合作为问答对的问题"
    prompt = prompt1.replace("{{此处替换成你的内容}}", text_content)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": content}
    ]
    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False
    )
    print("耗时", time.time() - start_time)
    return response.choices[0].message.content


def generate_qa(text_content, question_text=None):
    prompt = prompt2.replace("{{此处替换成你上一步生成的问题}}", question_text).replace("{{此处替换成你的内容}}", text_content)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "拼成问答对"}
    ]
    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False
    )
    print("耗时", time.time() - start_time)
    return response.choices[0].message.content


def write_to_file(content, file_path, output_dir):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    base_name = os.path.basename(file_path)
    output_file_name = f"qa_{base_name}_{timestamp}.txt"
    output_path = os.path.join(output_dir, output_file_name)
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"File '{output_path}' has been created and written.")


def read_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:  # 指定编码为 utf-8
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")


def process_file(file_path, output_dir):
    text_content = read_file(file_path)
    print(f'Processing file: {file_path}')
    print('text_content\n', text_content)
    question_text = generate_question(text_content=text_content, more=True)
    print('question_text\n', question_text)
    qa_text = generate_qa(text_content=text_content, question_text=question_text)
    print('qa_text\n', qa_text)
    write_to_file(qa_text, file_path, output_dir)


def process_directory(directory):
    # 获取输入目录的上一级目录
    parent_dir = os.path.dirname(directory)
    # 创建输出目录路径
    output_dir = os.path.join(parent_dir, "outputQA")
    # 如果输出目录不存在，则创建
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    for root, dirs, files in os.walk(directory):
        for file_name in files:
            if file_name.endswith(".txt"):  # 只处理txt文件
                file_path = os.path.join(root, file_name)
                process_file(file_path, output_dir)


if __name__ == "__main__":
    directory = "/root/rag_project/data/crawled"  # 替换为你的输入文件目录
    process_directory(directory)
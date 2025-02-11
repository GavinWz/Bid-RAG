import datetime
import re
import time
import os
from openai import OpenAI

# 替换为您自己的DeepSeek API密钥
api_key = 'sk-GTJJepLkpBjc3a3752B117049fEc489f9c63F8944cDdA0Ec'
client = OpenAI(api_key=api_key, base_url="https://openai.sohoyo.io/v1/")
model = "gpt-4o-mini"

# # 替换为您自己的DeepSeek API密钥
# api_key = 'sk-Jz6bVV1X8W0By9UYCVvasM3rZTzEqtB2LktxDetpXdqtDZBZ'
# client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")

# model = "moonshot-v1-8k"


# # ollama
# from langchain_ollama import OllamaLLM
# model = OllamaLLM(model="glm4-9b")

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

prompt2 = '''
你是一个阅读理解专家，你擅长结合我提供的文本回答我的问题，并将结果以标准的sharegpt的one shot格式返回，以便我利用你的回答做大模型微调。
我提供的文本可能会涉及多个方面，包括但不限于：商业招投标，采购，企业管理，政府政策，法律条文，商品信息，企业概况，舆情信息等等。

我的提供的文本如下：

"""

{{此处替换成你的内容}}

"""
我的问题如下：
"""

{{此处替换成你上一步生成的问题}}

"""

结合文本回答问题，以下是具体的回答要求：
1. 答案要全面，多使用我的提供的信息，内容要更丰富，尽量避免使用指代不明确的代词。

2. 你必须使用标准的sharegpt的one shot格式来输出回答，使用json格式输出，以下是个例子：
```json
{
  "messages": [
    {
      "role": "system",
      "content": ""
    },
    {
      "role": "user",
      "content": "{{我的问题}}"
    },
    {
      "role": "assistant",
      "content": "{{你的答案}}"
    }
  ]
}
```

3. 不要生成任何的HTML标签。

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

def generate_question_ollama(text_content, more=False):
    content = "生成适合作为问答对的问题"
    if more:
        content = "尽可能多生成适合作为问答对的问题"
    prompt = prompt1.replace("{{此处替换成你的内容}}", text_content)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": content}
    ]
    start_time = time.time()

    response = model.invoke(messages[0]['content'] + '\n\n' + messages[1]['content'])
    # response = model.invoke(messages)
    print("耗时", time.time() - start_time)
    response = re.sub(r'\n[0-9]+. ', '', response)
    return response

def generate_qa(text_content, question_text):
    prompt = prompt2.replace("{{此处替换成你上一步生成的问题}}", question_text).replace("{{此处替换成你的内容}}", text_content)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "生成问答对"}
    ]
    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=False
    )
    print("耗时", time.time() - start_time)
    return response.choices[0].message.content.strip().strip('```json').strip('```').strip()


def generate_qa_ollama(text_content, question_text):
    prompt = prompt2.replace("{{此处替换成你上一步生成的问题}}", question_text).replace("{{此处替换成你的内容}}", text_content)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "生成问答对"}
    ]
    start_time = time.time()

    response = model.invoke(messages[0]['content'] + '\n\n' + messages[1]['content'])
    # response = model.invoke(messages)
    print("耗时", time.time() - start_time)
    return str(response).strip().strip('```json').strip('```').strip()


def write_to_file(content, output_path):
    with open(output_path, "w", encoding="utf-8") as file:
        file.write('[\n')
        file.write(content)
        file.write(']\n')
    print(f"File '{output_path}' has been created and written.")


def read_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:  # 指定编码为 utf-8
            content = file.read()
            if len(content.strip()) == 0:
                return None
        return os.path.basename(file_path) + '\n' + content
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")


def process_file(file_path, output_dir):
    # 将所有问答对写入文件
    base_name = os.path.basename(file_path)
    output_file_name = f"qa_{base_name}.json"
    output_path = os.path.join(output_dir, output_file_name)

    # 如果输出文件已经存在，则跳过它
    if os.path.exists(output_path):
        return

    # 如果文章为空，则跳过它
    text_content = read_file(file_path)
    if text_content is None:
        return

    print(f'Processing file: {file_path}')
    print('text_content\n', text_content)

    # 生成问题列表
    question_text = generate_question(text_content=text_content, more=True)
    questions = re.split(r'\n+', question_text.strip().strip('```').strip())
    print('Generated questions:\n', questions)

    # 循环处理每个问题
    qa_pairs = []
    for question in questions:
        if question.strip():  # 确保问题不为空
            qa_text = generate_qa(text_content=text_content, question_text=question)
            qa_pairs.append(qa_text)
            print(f'Generated QA for question: {question}\n', qa_text)

    # 将生成的问答对写入文件
    write_to_file(",\n\n".join(qa_pairs), output_path)


def process_directory(input_dir, output_dir):
    # 获取输入目录的上一级目录
    parent_dir = os.path.dirname(input_dir)

    # 如果输出目录不存在，则创建
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    for root, dirs, files in os.walk(input_dir):
        for file_name in files:
            if file_name.endswith(".txt"):  # 只处理txt文件
                file_path = os.path.join(root, file_name)
                process_file(file_path, output_dir)
    
    print("该文件夹下所有文件已经被处理完毕。")


if __name__ == "__main__":
    # directory = "/root/rag_project/data/crawled"  # 替换为你的输入文件目录
    input_dir = "/root/rag_project/data/crawled/安徽合肥公共资源交易中心"  # 替换为你的输入文件目录
    output_dir = "/root/rag_project/data/qa" 
    process_directory(input_dir, output_dir)
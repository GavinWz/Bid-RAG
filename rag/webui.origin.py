import os

import gradio as gr
from langchain_ollama import OllamaLLM
from pymilvus import MilvusClient

from rag.config import Config
import rag_answer


def concat_history(chat_history):
    if chat_history is None or len(chat_history) == 0:
        return "在此之前没有对话记录....."
    history = ""
    for query, answer in chat_history:
        history += f"\nUser query: {query}\nYour answer:{answer}\n"
    return history

def predict_stream(user_input, chat_history):
    """
    用户点击'发送'后，Gradio会调用此函数。
    user_input: 用户新输入的消息
    chat_history: 聊天历史（列表），其中每个元素可为 (用户消息, AI 回答)
    """
    # 召回用户查询
    knowledge = rag_answer.recall(user_input, client, config, embedding_model)
    prompt = rag_answer.prompt_genarate(user_input, knowledge)
    print(prompt)
    # 先将用户输入加入到聊天记录
    history = concat_history(chat_history)
    chat_history = chat_history + [(prompt, "")]
    user_query = (
            f"回答用户问题：{prompt}"
            f"以下是你和用户的对话历史:{history}"
            )

    # 调用模型生成。此处演示式地直接把 user_input 作为 prompt
    # 如果 OllamaLLM.invoke() 支持 stream=True，就可以这样：
    # response_chunks = llm.invoke(user_input, stream=True)
    # 如果不支持，可以试试直接迭代 llm.invoke(user_input) 是否可行
    response_chunks = llm.stream(user_query)

    partial_response = ""
    # 逐块读取
    for chunk in response_chunks:
        partial_response += chunk
        # 更新聊天记录中最新的一条 (即最后一条) 的 AI 回答
        chat_history[-1] = (user_input, partial_response)
        # 使用 yield 让前端实时收到更新
        yield chat_history, ""

    # 最终结果再写入一次，保证最后一次状态也更新到前端
    chat_history[-1] = (user_input, partial_response)
    print(chat_history)
    yield chat_history, ""

def predict_stream2(user_input, chat_history):
    """
    用户点击'发送'后，Gradio会调用此函数。
    user_input: 用户新输入的消息
    chat_history: 聊天历史（列表），其中每个元素可为 (用户消息, AI 回答)
    """
    # 先将用户输入加入到聊天记录，并立即显示
    chat_history = chat_history + [(user_input, "")]
    yield chat_history, ""  # 先显示用户输入

    # 召回用户查询
    knowledge = rag_answer.recall(user_input, client, config, embedding_model)
    prompt = rag_answer.prompt_genarate(user_input, knowledge)
    print(prompt)

    # 生成模型输入
    history = concat_history(chat_history)
    user_query = (
        f"回答用户问题：{prompt}"
        f"以下是你和用户的对话历史:{history}"
    )

    # 调用模型生成回复
    response_chunks = llm.stream(user_query)

    partial_response = ""
    # 逐块读取模型回复
    for chunk in response_chunks:
        partial_response += chunk
        # 更新聊天记录中最新的一条 (即最后一条) 的 AI 回答
        chat_history[-1] = (user_input, partial_response)
        # 使用 yield 让前端实时收到更新
        yield chat_history, ""

    # 最终结果再写入一次，保证最后一次状态也更新到前端
    chat_history[-1] = (user_input, partial_response)
    print(chat_history)
    yield chat_history, ""

if __name__ == '__main__':
    # 初始化模型。需要确认 langchain_ollama 是否支持流式输出。
    # 如果要使用流式，需要在 OllamaLLM 中加上 streaming=True 等参数，或者在 invoke 时指定。
    llm = OllamaLLM(model="glm4-9b")

    config = Config()
    db_dir = config.db_dir
    db_name = config.db_name
    client = MilvusClient(os.path.join(db_dir, db_name))

    embedding_model = rag_answer.load_embedding_model(config)

    with gr.Blocks() as demo:
        gr.Markdown("<h3 align='center'>基于 GLM4-9B 的聊天演示</h3>")

        # 聊天记录显示
        chatbot = gr.Chatbot(label="历史聊天记录")
        # 用户输入
        user_input = gr.Textbox(lines=2, placeholder="请输入你的问题...")

        # 发送按钮
        send_button = gr.Button("发送")

        # 当用户点击按钮时触发 predict_stream
        # outputs=[chatbot, user_input] 的意思是，每次产生新输出时更新 Chatbot 并清空输入框
        send_button.click(
            fn=predict_stream,
            inputs=[user_input, chatbot],
            outputs=[chatbot, user_input],
            queue=True
        )

    demo.launch(server_name='0.0.0.0', server_port=7860)

import gradio as gr
import time

def stream_response(message, history):
    # 模拟流式生成，逐词返回
    response = ""
    for chunk in ["你好", "！", "我是", "流式", "聊天", "机器人。"]:
        response += chunk
        time.sleep(0.1)  # 模拟处理延迟
        yield response

# 创建 ChatInterface 并启动
gr.ChatInterface(
    fn=stream_response,
    title="流式聊天演示",
).launch()
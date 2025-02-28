import gradio as gr
from rag_new.agent import answer, stream_answer


def start_chatbot():
    gr.ChatInterface(
        fn=stream_answer,
        chatbot=gr.Chatbot(height=500, value=[("您好", "我是小招，我将尽力帮助您解决问题。")]),
        textbox=gr.Textbox(placeholder="请输入您的内容", container=False, scale=7),
        title="招投标AI客服",
        theme="soft",
        examples=["", "", ""],
        retry_btn=None,
        submit_btn="发送",
        undo_btn="删除前言",
        clear_btn="清空",
    ).queue().launch(server_name="127.0.0.1", server_port=7001)

if __name__ == '__main__':
    start_chatbot()
import gradio as gr
from rag import rag_answer_new
from utils import concat_history, load_everything

class ChatBotGradio():
    def __init__(self, config, model, client, embedding_model):
        self.config = config
        self.model = model
        self.client = client
        self.embedding_model = embedding_model
        self.is_generating = False
        self.messages = []
        # 使用 JavaScript 实现 Shift + Enter 换行，并在生成时禁用回车键
        self.js_shift_enter_newline = """
            function handleKeyDown(event) {
                const textbox = document.querySelector("textarea");
                if (!textbox) return;

                // 如果按下 Shift + Enter，插入换行符
                if (event.key === "Enter" && event.shiftKey) {
                    event.preventDefault();
                    const start = textbox.selectionStart;
                    const end = textbox.selectionEnd;
                    const value = textbox.value;
                    textbox.value = value.substring(0, start) + "\n" + value.substring(end);
                    textbox.selectionStart = textbox.selectionEnd = start + 1;
                    return;
                }

                // 如果正在生成回复，阻止回车键的默认行为
                if (self.is_generating === true && event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    return;
                }
            }

            function setupKeyHandlers() {
                const textbox = document.querySelector("textarea");
                if (textbox) {
                    textbox.addEventListener("keydown", handleKeyDown);
                }
            }

            // 确保在页面加载后设置键盘事件监听器
            document.addEventListener("DOMContentLoaded", setupKeyHandlers);
            """    
        self.rag_module = rag_answer_new.RagModule(config, model, client, embedding_model)
    

    def update_chatbot(self, user_input, chat_history):
        """
        在用户按下回车或点击按钮时，立即将用户输入添加到聊天记录中。
        """
        # 检查用户输入是否为空
        if not user_input.strip():
            chat_history = chat_history + [("", "请输入有效的问题...")]
            return chat_history, "", ""  # 返回 chat_history, user_input, user_input_tmp

        # 检查生成状态，如果正在生成，则不更新聊天记录
        if self.is_generating:
            return chat_history, user_input, user_input

        self.is_generating = True
        chat_history = chat_history + [(user_input, "")]
        return chat_history, "", user_input  # 返回 chat_history, 清空 user_input, 并更新 user_input_tmp

    def start_new_chat(self, chat_history):
        """
        清空聊天记录并重置生成状态
        """
        chat_history = []  # 清空聊天记录
        self.is_generating = False  # 强制中断生成过程
        self.messages = []
        return chat_history

    def toggle_interaction(self):
        """
        根据生成状态动态禁用/启用发送按钮
        """
        return {
            self.send_button: gr.update(interactive=not self.is_generating),
            self.new_chat_button: gr.update(interactive=True),  # 始终保持“开启新对话”按钮可用
        }


    def predict_stream(self, user_input, chat_history):
        """
        用户点击'发送'后，Gradio会调用此函数。
        user_input: 用户新输入的消息
        chat_history: 聊天历史（列表），其中每个元素可为 (用户消息, AI 回答)
        """
        
        self.is_generating = True

        # 调用模型生成回复
        # response_chunks = self.rag_module.answer_with_rag(user_input, self.messages)
        response_chunks = self.rag_module.answer_with_rag(user_input, stream=True)

        partial_response = ""
        # 逐块读取模型回复
        for chunk in response_chunks:
            # 检查生成状态是否被中断
            if not self.is_generating:
                chat_history = []
                yield chat_history
                break  # 如果生成状态被中断，停止生成
            partial_response += chunk.content
            # 更新聊天记录中最新的一条 (即最后一条) 的 AI 回答
            chat_history[-1] = (user_input, partial_response)
            # 使用 yield 让前端实时收到更新
            yield chat_history

        # 如果生成过程未被中断，最终结果再写入一次
        if self.is_generating:
            chat_history[-1] = (user_input, partial_response)
            print(chat_history)
            yield chat_history
        
        self.is_generating = False
        self.messages.append(("assistant", partial_response))

    def launch(self):
        with gr.Blocks() as demo:
            gr.Markdown("<h3 align='center'>基于 GLM4-9B 的聊天演示</h3>")

            # 聊天记录显示
            self.chatbot = gr.Chatbot(label="历史聊天记录")
            # 用户输入
            self.user_input = gr.Textbox(lines=1, placeholder="请输入你的问题...")
            # 使用 State 来保存临时的用户输入
            self.user_input_tmp = gr.State("")
            # 发送按钮
            self.send_button = gr.Button("发送")
            # 开启新对话按钮
            self.new_chat_button = gr.Button("开启新对话")

            # 当用户点击按钮时，先更新聊天记录
            self.send_button.click(
                fn=self.update_chatbot,
                inputs=[self.user_input, self.chatbot],
                outputs=[self.chatbot, self.user_input, self.user_input_tmp],  # 更新 chat_history, user_input, user_input_tmp
                queue=False 
            ).then(
                fn=self.toggle_interaction,  # 在更新聊天记录后调用 toggle_interaction
                inputs=[],
                outputs=[self.send_button, self.new_chat_button],
                queue=False
            ).then(
                fn=self.predict_stream,
                inputs=[self.user_input_tmp, self.chatbot],  # 使用 user_input_tmp 作为 predict_stream 的输入
                outputs=[self.chatbot],
                queue=True 
            ).then(
                fn=self.toggle_interaction,  # 在生成完成后再次调用 toggle_interaction
                inputs=[],
                outputs=[self.send_button, self.new_chat_button],
                queue=False
            )

            # 当用户按下回车键时也触发相同的事件
            def handle_submit(user_input, chat_history):
                # 如果正在生成回复，则不执行任何操作，并保留输入框的内容
                if self.is_generating:
                    return chat_history, user_input, user_input
                # 否则正常执行 update_chatbot 和 predict_stream
                return self.update_chatbot(user_input, chat_history)

            self.user_input.submit(
                fn=handle_submit,
                inputs=[self.user_input, self.chatbot],
                outputs=[self.chatbot, self.user_input, self.user_input_tmp],  # 更新 chat_history, user_input, user_input_tmp
                queue=False  
            ).then(
                fn=self.toggle_interaction,  # 在更新聊天记录后调用 toggle_interaction
                inputs=[],
                outputs=[self.send_button, self.new_chat_button],
                queue=False
            ).then(
                fn=self.predict_stream,
                inputs=[self.user_input_tmp, self.chatbot],  # 使用 user_input_tmp 作为 predict_stream 的输入
                outputs=[self.chatbot],
                queue=True  
            ).then(
                fn=self.toggle_interaction,  # 在生成完成后再次调用 toggle_interaction
                inputs=[],
                outputs=[self.send_button, self.new_chat_button],
                queue=False
            )

            # 当用户点击“开启新对话”按钮时，清空聊天记录并重置生成状态
            self.new_chat_button.click(
                fn=self.start_new_chat,
                inputs=[self.chatbot],
                outputs=[self.chatbot],
                queue=False  
            ).then(
                fn=self.toggle_interaction,  # 在清空聊天记录后调用 toggle_interaction
                inputs=[],
                outputs=[self.send_button, self.new_chat_button],
                queue=False
            )

        # 在 Blocks 对象创建后注入 JavaScript 代码
        demo.custom_js = self.js_shift_enter_newline

        demo.launch(server_name='0.0.0.0', server_port=7100)


if __name__ == '__main__':
    config, model, client, embedding_model = load_everything()
    bot = ChatBotGradio(config, model, client, embedding_model)
    bot.launch()
    
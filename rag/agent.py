from rag.config import Config
from rag import rag_answer_new, config, sql_answer
from langchain.agents import Tool, initialize_agent
from langchain.memory import ConversationBufferMemory
from rag.utils import load_everything
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
# from openai import OpenAI
# from langchain.llms import OpenAI
from langchain_openai import OpenAI, ChatOpenAI


class Agent:
    def __init__(self):
        self.config = Config()
        config, client, embedding_model = load_everything()
        self.llm = OpenAI(api_key=config.api_key, base_url=config.base_url, model='glm4-9b')
        self.llm = ChatOpenAI(
            api_key="sk-SnDuQq9ZxxOgkMAq3d22C813034649D5A8E850D8C82a06Fa",
            base_url="https://aihubmix.com/v1/",
            model="gpt-4o",
            streaming=True
        )

        self.rag_module = rag_answer_new.RagModule(config, client, embedding_model)
        self.sql_module = sql_answer.SqlModule(config, client, embedding_model, self.rag_module)

        rag_answer_func = lambda input: self.rag_module.answer_with_rag(input, stream=False)
        sql_answer_func = lambda input: self.sql_module.answer_with_mysql(input)

        rag_answer_tool = Tool(name='Rag Answer Tool', func=rag_answer_func, 
                    description="""使用检索增强生成（RAG）的方法，从向量数据库中取答案。
                    向量数据库中保存的信息主要是关于：商业招投标，采购，企业管理，政府政策，法律条文，商品信息，企业概况，舆情信息等等。
                    需要一个输入：query_text, 是用户的原始问题，是字符串类型。
                    输出结果是一个字符串，是模型生成的答案。
                    """
                    )
        
        sql_answer_tool = Tool(name='Retrieve from Database', func=sql_answer_func,
                    description="""该函数会根据用户的问题，从关系型数据库中找到相应的结果。
                    需要一个输入:query_text，它是用户的输入，是字符串类型。
                    数据库中的表有：项目基本信息、采购公告、项目登记、中标结果、中标结果通知。
                    如果认为用户的问题和这些表有关，则将用户的原始问题输入到这个函数中，该函数会直接给出相应回答。
                    如果该函数的返回结果是"查询失败"，则调用Rag Answer Tool。
                    """
                    )
        
        self.tools = [rag_answer_tool, sql_answer_tool]

    def answer_with_agent(self, query, chat_history, stream=True):
        agent = initialize_agent(
            self.tools,
            self.llm,
            agent="chat-conversational-react-description",
            verbose=True,
            handle_parsing_errors=True
        )
        if stream:
            response = agent.stream({"input": query, "chat_history": chat_history})
        else:
            response = agent.invoke({"input": query, "chat_history": chat_history})


a = Agent()

agent = initialize_agent(
    [],
    a.llm,
    agent="chat-conversational-react-description", 
    verbose=True,
    handle_parsing_errors=True
)

chat_history = []

while True:
    human = input()
    response = agent.stream({"input": human, "chat_history": chat_history})
    assistant = ""
    for chunk in response:
        if 'output' in chunk:
            print(chunk['output'], end='')
            assistant += chunk['output']

    chat_history.append(("human", human))
    chat_history.append(("assistant", assistant))
# response = agent.invoke("《加快推进数字经济高质量发展行动方案（2024—2026年）》的主要目标是什么？")
# print(response)
# response = agent.invoke("我刚刚问了你什么问题？")
# print(response)
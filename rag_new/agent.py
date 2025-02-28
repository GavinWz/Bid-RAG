import time

from elasticsearch import Elasticsearch
from langchain import hub
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferWindowMemory
from langchain.retrievers import EnsembleRetriever
from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool, Tool
from langchain_milvus import Milvus
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain_community.retrievers import (
    ElasticSearchBM25Retriever,
)
from rag_new.utils import load_embedding_model, load_vec_db
from rag_new.config import Config

'''
模型定义和初始化
'''
config = Config()
gpt_llm = ChatOpenAI(
    api_key="sk-SnDuQq9ZxxOgkMAq3d22C813034649D5A8E850D8C82a06Fa",
    base_url="https://aihubmix.com/v1/",
    model="gpt-4o",
)

# glm_llm = ChatOpenAI(
#     api_key=config.api_key,
#     base_url=config.base_url,
#     model=config.model
# )
embedding_model = load_embedding_model(config)
memory = ConversationBufferWindowMemory(memory_key="chat_history", return_messages=True, k=5)

system_prompt = '''
你是一个合肥市招投标行业的问答机器人，你了解的知识涵盖了商业招投标，采购，企业管理，政府政策，法律条文，商品信息，企业概况，\
舆情信息，招投标项目信息，交易信息，采购信息等等。

而且，你擅长使用工具辅助自己回答用户问题，回答用户问题时，请使用中文回答。
'''

'''
RAG检索
'''
def load_retriever(config=config, embedding_model=embedding_model):
    db = Milvus(
        embedding_function=embedding_model,
        connection_args={
            'uri': 'http://127.0.0.1:19530'
        },
        collection_name=config.collection_name
    )
    dense_retriever = db.as_retriever(
        search_kwargs={
            'k': 5,
            'score_threshold': 0.5,
            'param': {
                'metric_type': 'COSINE',
                "params": {
                    "ef": 64
                }
            }
        }
    )

    elasticsearch_url = "http://127.0.0.1:9200"

    sparse_retriever = ElasticSearchBM25Retriever(
        client=Elasticsearch(elasticsearch_url),
        index_name="langchain-index-4"
    )
    retriever = EnsembleRetriever(
        retrievers=[dense_retriever, sparse_retriever],
        weights=[0.9, 0.1],
    )
    return retriever


@tool
def retrieve_by_rag(query):
    '''
    借助RAG系统，查询招投标行业相关政策、法律法规、新闻等信息，以便更好地回答用户问题。
    '''
    db_retriever = load_retriever(config, embedding_model)
    result = db_retriever.invoke(query)
    # "安徽省人民政府要求哪些主体贯彻落实《关于进一步提振市场信心促进经济平稳健康运行的若干政策举措》？"
    # result = db.vectorstore.similarity_search_with_score("安徽省人民政府要求哪些主体贯彻落实《关于进一步提振市场信心促进经济平稳健康运行的若干政策举措》？")
    print(result[config.topk])
    return result[config.topk]


'''
SQL检索
'''
db = SQLDatabase.from_uri('mysql+pymysql://root:root_password@47.99.156.131/rag')
toolkit = SQLDatabaseToolkit(db=db, llm=gpt_llm)
sql_agent = create_sql_agent(llm=gpt_llm, toolkit=toolkit, verbose=True, agent_type=AgentType.OPENAI_FUNCTIONS)


class SqlField(BaseModel):
    query: str = Field(description="用户的输入")


@tool("answer_according_database", args_schema=SqlField)
def answer_according_database(query: str):
    '''
    本地的MySQL数据库中有以下表结构：
    商品价格表  (商品id, 商品名称, 商品大类, 商品中类, 商品小类, 起批量, 最大销售批量, 商品数量单位, 商品价格, 商品价格单位, 售价)

    商品信息表  (商品id, 商品名称, 商品大类, 商品中类, 商品小类, 商品列表链接, 商品详情页链接, 商品价格, 商品细类, 品牌名称, 商品参数, 买方保障, 展示价格, 最小批量, 供应商名称, 供应商业务内容, 联系人名称, 联系方式, 联系人邮箱, 省份, 地区, 城市, 供应商地址, 采集日期)

    项目中标表  (项目id, 中标id, 项目名称, 项目简号, 项目标题, 项目阶段, 公告发布时间, 中标金额_费率, 项目终止原因, 标段编号, 标段名称, 供应商名称, 供应商地址, 统一社会信用代码, 发放日期, 开标日期, 开标地点, 中标结果正文, 附件)

    项目公告表  (项目id, 项目名称, 项目简号, 项目标题, 招标公告发布时间, 投标截止时间, 文件上传截至时间, 最高限价, 合同履行期限, 申请人的资格要求, 采购需求, 招标单位名称, 招标单位地址, 招标单位联系方式, 采购代理机构名称, 采购代理机构地址, 采购代理机构联系方式, 项目联系人, 项目联系人电话, 招标公告正文, 招标公告-附件)

    项目表  (项目id, 项目名称, 项目简号, 项目标题, 城市地区, 招标项目大类, 项目小类, 项目发布日期, 项目阶段, 招标单位名称, 招标方式, 是否PPP项目, 预算金额, 财政委托编号, 交易平台, 项目建立时间, 详情页链接)

    如果用户的提问和这些表相关，则调用此工具。该工具将从MySQL表中查询到用户想要的信息，并用自然语言回答用户问题，如果数据库查询失败，则该工具应该返回：“查询失败”
    '''
    result = sql_agent.invoke({"input": query})

    return result


def create_agent():
    tools = [answer_according_database, retrieve_by_rag]

    agent = initialize_agent(
        tools,
        gpt_llm,
        agent="chat-conversational-react-description",
        verbose=True,
        handle_parsing_errors=True,
        memory=memory,
        agent_kwargs={
            "system_message": system_prompt
        }
    )
    return agent


def create_custom_agent():
    tools = [answer_according_database, retrieve_by_rag]
    # agent =


def answer(query, gradio_history):
    agent = create_agent()
    response = agent.invoke({"input": query})
    gradio_history.append((query, response['output']))
    return response['output']


def stream_answer(query, gradio_history):
    agent = create_agent()
    response = agent.invoke({"input": query})['output']

    partial_response = ''
    for chunk in response:
        partial_response += chunk
        # 更新聊天记录中最新的一条 (即最后一条) 的 AI 回答
        gradio_history[-1] = (query, partial_response)
        # 使用 yield 让前端实时收到更新
        yield partial_response

if __name__ == '__main__':
    # tool_call_demo()
    stream_answer('hi', [])
    # prompt_demo()

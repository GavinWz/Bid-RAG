import asyncio

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate, AIMessagePromptTemplate, \
    PromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from rag.config import Config
from langchain_core.tools import tool

config = Config()


def v0():
    # 基础功能
    llm = ChatOpenAI(api_key=config.api_key, base_url=config.base_url, model='glm4-9b')

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("你是一个{field}领域的问答机器人，请回答用户问题。"),
        MessagesPlaceholder(variable_name='history'),
        HumanMessagePromptTemplate.from_template("{input}"),
    ])
    # prompt = prompt_template.invoke({'field': "教育", 'input': "为什么要学习？", 'history':[HumanMessage("你叫什么？"), AIMessage("我没有叫。")]})

    # print(prompt)
    chain = prompt_template | llm | StrOutputParser()
    history = [HumanMessage("你叫什么？"), AIMessage("我没有叫。")]

    while True:
        user_input = input()
        ai_message = chain.invoke({'field': "教育", 'input': user_input, 'history': history})

        history.append(HumanMessage(user_input))
        history.append(AIMessage(ai_message))
        print(ai_message)


def v1():
    # 流式调用
    llm = ChatOpenAI(api_key=config.api_key, base_url=config.base_url, model='glm4-9b')
    prompt = ChatPromptTemplate.from_messages([
        ('system', "你是一个{field}领域的问答机器人，请回答用户问题。"),
        ('user', "论述为什么要学习？学习有什么好处？")
    ])
    chain = prompt | llm | StrOutputParser()

    async def async_stream():
        async for chunk in chain.astream({'field': "教育"}):
            print(chunk, end="", flush=True)

    asyncio.run(async_stream())


def v2():
    # 多轮对话
    from langchain_core.runnables.history import RunnableWithMessageHistory, BaseChatMessageHistory
    from langchain_community.chat_message_histories import ChatMessageHistory
    llm = ChatOpenAI(api_key=config.api_key, base_url=config.base_url, model='glm4-9b')
    prompt = ChatPromptTemplate.from_messages([
        ('system', "你是一个{field}领域的问答机器人，请回答用户问题。"),
        MessagesPlaceholder('history'),
        ('user', "{input}")
    ])
    runnable = prompt | llm | StrOutputParser()

    store = {}

    # 定义一个获取会话历史的的函数
    def get_session_history(session_id) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

    with_message_history = RunnableWithMessageHistory(
        runnable,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history"
    )

    response = with_message_history.stream(
        {"input": "为什么要学习？", "field": "教育"},
        config={"configurable": {"session_id": "123"}}
    )
    for chunk in response:
        print(chunk, end="", flush=True)

    response = with_message_history.stream(
        {"input": "我刚刚问了你什么问题？", "field": "教育"},
        config={"configurable": {"session_id": "123"}}
    )
    for chunk in response:
        print(chunk, end="", flush=True)


def v3():
    # JSON Parser自定义键
    class Population(BaseModel):
        country: str = Field(description="国家名称")
        population: str = Field(description="人口数量")

    query = "给出世界上最有名的10个国家和他们的人口数量。"
    parser = JsonOutputParser(pydantic_object=Population)

    llm = ChatOpenAI(api_key=config.api_key, base_url=config.base_url, model='glm4-9b')
    # prompt = ChatPromptTemplate.from_messages([
    #     ('system', "你是一个问答机器人，请回答用户问题。"),
    #     ('user', "{input}")
    # ])
    prompt = PromptTemplate(
        template="你是一个问答机器人，请回答用户问题：\n{format_instructions}\n{input}\n",
        input_variables=["input"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser
    response = chain.invoke({'input': query})
    print(response)
    # for chunk in response:
    #     print(chunk.content, end="", flush=True)


def v4():
    # 工具定义和调用
    from langchain_core.tools import tool

    @tool
    def add(a: int, b: int) -> int:
        '''
        将两个整数相加
        '''
        return a + b

    print(add.name)
    print(add.description)
    print(add.args)

    # 异步工具的定义

    @tool
    async def add_sync(a: int, b: int) -> int:
        '''
        将两个整数相加
        '''
        return a + b

def v5():
    # 自定义程度较高的工具定义
    from pydantic import BaseModel, Field  # 注意，这里的BaseModel和Field是from pydantic而不是langchain
    class AddInput(BaseModel):
        a: int = Field(description="被加数")
        b: int = Field(description="加数")

    @tool('add_tool', args_schema=AddInput, return_direct=True)
    def add(a: int, b: int) -> int:
        '''
        将两个整数相加
        '''
        return a + b

    print(add.name)
    print(add.description)
    print(add.args)

def v6():
    # langchain中的StructuredTool, 将同步调用和异步调用集成在一起
    from langchain_core.tools import StructuredTool
    def add(a: int, b: int) -> int:
        '''计算两数之和'''
        return a + b

    async def async_add(a: int, b: int) -> int:
        '''计算两数之和'''
        return a + b

    async def main():
        calculator = StructuredTool.from_function(func=add, coroutine=async_add)
        print(calculator.invoke({"a": 12, "b":13}))
        print(await calculator.ainvoke({"a": 12, "b": 13}))

    asyncio.run(main())

def v7():
    # StructuredTool和pydantic自定义参数组合起来使用
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field  # 注意，这里的BaseModel和Field是from pydantic而不是langchain
    class AddInput(BaseModel):
        a: int = Field(description="被加数")
        b: int = Field(description="加数")

    def add(a: int, b: int) -> int:
        '''计算两数之和'''
        return a + b
    async def async_add(a: int, b: int) -> int:
        '''计算两数之和'''
        return a + b

    async def main():
        calculator = StructuredTool.from_function(
            func=add,
            name="Calculator",
            description="两数之和",
            args_schema=AddInput,
            return_direct=True
        )
        print(calculator.invoke({"a": 12, "b":4}))
        print(await calculator.ainvoke({"a": 12, "b": 6}))
        print(calculator.description)
        print(calculator.args)
    asyncio.run(main())


if __name__ == '__main__':
    v7()

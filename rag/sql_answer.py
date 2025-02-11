import pymysql
from openai import OpenAI

import rag.rag_answer
from rag.utils import load_everything


class SqlModule():
    def __init__(self, config, model, client, embedding_model, rag_module):
        self.config = config
        self.model = model
        self.client = client
        self.embedding_model = embedding_model
        self.rag_module = rag_module

    def nl2sql(self, query, client):
        system_prompt = """你是一个SQL专家，你擅长根据用户描述和以下的表结构生成对应的SQL语句。
    该数据库是一个关于企业招投标公示的数据库，包含`项目基本信息`,` 采购公告`, `项目登记`, `中标结果`, `中标结果通知`这五张表。

    -- ----------------------------
    -- Table structure for 中标结果
    -- ----------------------------
    `中标结果ID` int ,
    `项目ID` int,
    `中标结果公告标题` ,
    `中标结果正文` ,
    `附件` ,
    PRIMARY KEY (`中标结果ID`) USING BTREE,
    INDEX `项目ID`(`项目ID` ASC) USING BTREE,
    -- ----------------------------
    -- Table structure for 中标结果通知
    -- ----------------------------
    `中标结果通知ID` int ,
    `项目ID` int,
    `中标通知标题` ,
    `标段编号` ,
    `标段名称` ,
    `采购人` ,
    `代理机构` ,
    `中标金额_费率` ,
    `中标金额单位` ,
    `中标单位` ,
    `发放日期` date,
    `附件` ,
    PRIMARY KEY (`中标结果通知ID`) USING BTREE,
    INDEX `项目ID`(`项目ID` ASC) USING BTREE,

    -- ----------------------------
    -- Table structure for 基本信息
    -- ----------------------------
    `项目ID` int ,
    `标题` varchar(255) ,
    `发布日期` date,
    `城市地区` varchar(255) ,
    `文章标题` varchar(255) ,
    `链接` varchar(255) ,
    PRIMARY KEY (`项目ID`) USING BTREE

    -- ----------------------------
    -- Table structure for 采购公告
    -- ----------------------------
    `采购公告ID` int ,
    `项目ID` int,
    `采购人` ,
    `投标截止日期` date,
    `公告有效期` ,
    `公告标题` ,
    `项目代理机构地址` ,
    `附件` ,
    `公告正文` ,
    PRIMARY KEY (`采购公告ID`) USING BTREE,
    INDEX `项目ID`(`项目ID` ASC) USING BTREE,
  
    -- ----------------------------
    -- Table structure for 项目登记
    -- ----------------------------
    `项目登记ID` int,
    `项目ID` int,
    `项目名称` ,
    `项目简号` ,
    `采购人名称` ,
    `财政委托编号` ,
    `交易平台` ,
    `预算金额单位` ,
    `预算金额` ,
    `采购方式` ,
    `是否PPP项目` ,
    `监督部门编号` ,
    `监督部门名称` ,
    `代理机构` ,
    `项目建立时间` date,
    PRIMARY KEY (`项目登记ID`) USING BTREE,
    INDEX `项目ID`(`项目ID` ASC) USING BTREE,

    请根据以上的表结构，生成用户询问对应的SQL语句，并返回SQL语句。
    要求：
    1. 用markdown的code block格式返回SQL语句，仅输出这个code block，不要添加其他的任何描述性文字。
    2. 表名和字段名要严格和数据库表结构一致。
    3. SQL语句要符合SQL标准，不要有语法错误。
    4. SQL语句要尽可能简洁，不要有多余的表连接或子查询。
    5. SQL语句要尽可能高效，不要有性能问题。
    6. 尽可能多的返回你认为对解答用户询问有帮助的所有数据列。
    7. 如果根据以上的表结构无法生成用户询问对应的SQL语句，请返回"无法生成SQL语句"。
    """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.5,
        )
        result = completion.choices[0].message.content
        messages.append({
            "role": "assistant",
            "content": result
        })
        return result.strip().strip('```sql').strip('```')


    def get_mysql_connection(self):
        # Step 1: 配置数据库连接信息
        config = {
            "host": "localhost",        # 数据库主机地址
            "user": "root",    # 数据库用户名
            "password": "root_password",# 数据库密码
            "database": "rag" # 要连接的数据库
        }
        return pymysql.connect(**config)

    def sql_result2md_table(self, result, columns):
        md_table = "|".join(columns) + "\n"
        md_table += "|".join(["---"] * len(columns)) + "\n"
        for row in result:
            md_table += "|".join([str(cell) for cell in row]) + "\n"
        return md_table

    def sql_select(self, sql, connection: pymysql.Connection):
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        return result, columns

    def generate(self, query, md_table, client, stream):
        system_prompt = ("你是一个回答问题的助手，目前的系统中，用户会提出一个问题，我会根据用户的提问从MySql表中找到相关的答案，并使用Markdown"
                         "格式提供给你，请根据该结果回答用户的问题。（注意：直接回答用户的问题即可，不要让用户意识到这些数据是从数据库中查到的。）")
        
        user_prompt = f"""
        问题：
        ```
        {query}
        ```
        Mysql的查询结果：
        ```
        {md_table}
        ```
        """
        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = client.chat.completions.create(
            model="gpt-4",
            messages=message,
            temperature=0.5,
            stream=stream
        )

        if stream:
            return response
            # for chunk in response:
            #     if len(chunk.choices) > 0:
            #         content = chunk.choices[0].delta.content
            #         if content is not None:
            #             yield content
        else:
            return response.choices[0].message.content

    def answer_with_mysql(self, query, stream=False):
        # ========== 1. 大模型API设置，Mysql连接建立 ==========
        client = OpenAI(
            api_key = "sk-GTJJepLkpBjc3a3752B117049fEc489f9c63F8944cDdA0Ec",
            base_url = "https://openai.sohoyo.io/v1/"
        )
        connection = self.get_mysql_connection()
            
        # ========== 2. 生成SQL语句 ==========
        sql = self.nl2sql(query, client)
        print(sql)
        if '无法生成SQL语句' in sql:
            # 调用rag
            return '查询失败'

        # ========== 3. 执行SQL语句并返回结果 ==========
        result, columns = self.sql_select(sql, connection)

        # ========== 4. 将SQL结果转换为Markdown表格 ==========
        md_table = self.sql_result2md_table(result, columns)
        print(md_table)

        # ========== 5. 生成答案 ==========
        answer = self.generate(query, md_table, client, stream)
        print(answer)
        return answer

if __name__ == '__main__':
    query = '在2024年12月10日到2024年12月25日，合肥市公安局发布招标公告了吗？'
    config, model, client, embedding_model = load_everything()
    rag_module = rag.rag_answer.RagModule(config, model, client, embedding_model)
    sql_module = SqlModule(config, model, client, embedding_model, rag_module)
    response = sql_module.answer_with_mysql(query)
    for s in response:
        print(s, end='')
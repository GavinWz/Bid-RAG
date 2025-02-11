import json
import pymysql
from tqdm import tqdm


def create_basic_tables(connection):
    """
    只建 5 张表的初始结构，后续有新字段时会动态添加。
    """
    sql_basic_info = """
    CREATE TABLE IF NOT EXISTS `基本信息` (
      `项目ID` INT AUTO_INCREMENT PRIMARY KEY,
      `标题` VARCHAR(255),
      `发布日期` DATE,
      `城市地区` VARCHAR(255),
      `文章标题` VARCHAR(255),
      `链接` VARCHAR(255)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    sql_project_reg = """
    CREATE TABLE IF NOT EXISTS `项目登记` (
      `项目登记ID` INT AUTO_INCREMENT PRIMARY KEY,
      `项目ID` INT,
      FOREIGN KEY (`项目ID`) REFERENCES `基本信息`(`项目id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    sql_purchase_notice = """
    CREATE TABLE IF NOT EXISTS `采购公告` (
      `采购公告ID` INT AUTO_INCREMENT PRIMARY KEY,
      `项目ID` INT,
      FOREIGN KEY (`项目ID`) REFERENCES `基本信息`(`项目id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    sql_winning_result = """
    CREATE TABLE IF NOT EXISTS `中标结果` (
      `中标结果ID` INT AUTO_INCREMENT PRIMARY KEY,
      `项目ID` INT,
      FOREIGN KEY (`项目ID`) REFERENCES `基本信息`(`项目id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    sql_winning_notif = """
    CREATE TABLE IF NOT EXISTS `中标结果通知` (
      `中标结果通知ID` INT AUTO_INCREMENT PRIMARY KEY,
      `项目ID` INT,
      FOREIGN KEY (`项目ID`) REFERENCES `基本信息`(`项目id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_basic_info)
        cursor.execute(sql_project_reg)
        cursor.execute(sql_purchase_notice)
        cursor.execute(sql_winning_result)
        cursor.execute(sql_winning_notif)
    connection.commit()


def insert_basic_info(connection, json_data):
    """
    插入到表一：基本信息（固定字段）。
    """
    sql_basic = """
    INSERT INTO `基本信息`
    (`标题`, `发布日期`, `城市地区`, `文章标题`, `链接`)
    VALUES (%s, %s, %s, %s, %s)
    """

    title = json_data.get("标题", "")
    publish_date = json_data.get("发布日期", "")
    city_region = json_data.get("城市地区", "")
    article_title = json_data.get("文章标题", "")
    link = json_data.get("链接", "")

    with connection.cursor() as cursor:
        cursor.execute(sql_basic, (title, publish_date, city_region, article_title, link))
        project_id = cursor.lastrowid
    connection.commit()
    return project_id


def insert_dynamic_table(connection, table_name, project_id, data_dict):
    """
    将 data_dict 中所有键值对插入到指定中文表名下。
    若表中不存在相应的列，动态添加列后再插入。

    :param connection: 数据库连接
    :param table_name: 中文表名，如 "项目登记"
    :param project_id: 对应的 `基本信息` 中的外键项目ID
    :param data_dict: 要插入的 JSON 字典
    """
    if not data_dict:
        return  # 没有数据，不插入

    # 1. 查看表中已有字段
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
        existing_columns = {row["Field"] for row in cursor.fetchall()}

    # 2. 遍历 data_dict 的所有 key，如果不存在则通过 ALTER TABLE 动态添加
    #    在此示例中，统一使用 VARCHAR(255)，可自行扩展为 TEXT 等
    for k in data_dict.keys():
        if k not in existing_columns:
            if '日期' in k or '时间' in k:
                alter_sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{k}` DATE;"
            else:
                alter_sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{k}` TEXT;"
            with connection.cursor() as cursor:
                cursor.execute(alter_sql)
            connection.commit()
            existing_columns.add(k)

    # 3. 构造 INSERT 语句
    #    必备字段：项目ID，其余来自 data_dict.keys()
    columns = ["项目ID"]
    values = [project_id]
    for k, v in data_dict.items():
        if v is not None and len(v) > 0:
            columns.append(k)
            values.append(str(v))

    col_str = ", ".join([f"`{col}`" for col in columns])
    placeholders = ", ".join(["%s"] * len(columns))

    insert_sql = f"INSERT INTO `{table_name}` ({col_str}) VALUES ({placeholders})"

    with connection.cursor() as cursor:
        cursor.execute(insert_sql, values)

    connection.commit()

def create_connection():
    # 1. 连接 MySQL 数据库
    connection = pymysql.connect(
        host="localhost",
        user="root",
        password="root_password",
        db="rag",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

    # 2. 创建表（若不存在）
    create_basic_tables(connection)
    return connection


def main():
    # 1. 连接 MySQL 数据库
    connection = create_connection()

    try:
        # 3. 读取 JSONL 文件并写入
        with open("rag/安徽合肥公共资源交易中心-政府采购.jsonl", "r", encoding="utf-8") as f:
            for line in tqdm(f, desc="Processing ... "):
                line = line.strip()
                if not line:
                    continue
                json_obj = json.loads(line)

                # 3.1 先插入表一“基本信息”，拿到 project_id
                project_id = insert_basic_info(connection, json_obj)

                # 3.2 动态插入表二~表五
                #     我们用一个映射 dict 来对应 JSON 的键与中文表名
                table_map = {
                    "项目登记": "项目登记",
                    "采购公告": "采购公告",
                    "中标结果": "中标结果",
                    "中标结果通知": "中标结果通知"
                }
                for json_key, tbl_name in table_map.items():
                    sub_dict = json_obj.get(json_key, {})
                    if isinstance(sub_dict, dict):
                        insert_dynamic_table(connection, tbl_name, project_id, sub_dict)

    finally:
        connection.close()


if __name__ == "__main__":
    main()

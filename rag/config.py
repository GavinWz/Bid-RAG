import json

class Config():
    def __init__(
            self, 
            config_file = None,
            model = "glm4-9b",
            temperature = 0.8,
            num_predict = 2048,
            embedding_model_dir = '/root/models/embedding_models',
            embedding_model_name = 'distiluse-base-multilingual-cased-v2',  # 512维
            data_dir = '/root/rag_project/data/crawled/安徽合肥公共资源交易中心',
            db_dir = '/root/rag_project/vec_dbs',
            db_name = "bid_rag",
            collection_name = "policy",
            chunk_size = 4096,
            chunk_overlap = 1000,
            recall_threshold = 0.2,
            topk = 3
        ):
        # 如果有配置文件，则加载配置文件
        self.config_file = config_file
        if self.config_file is not None:
            self.load_config()
        # 否则，使用参数初始化
        else:
            self.model = model
            self.temperature = temperature
            self.num_predict = num_predict
            self.embedding_model_dir = embedding_model_dir
            # self.embedding_model_name = 'paraphrase-multilingual-MiniLM-L12-v2'  # 384维
            # self.embedding_model_name = 'conan-embedding-v1'   # 1792维
            self.embedding_model_name = embedding_model_name
            self.db_dir = db_dir
            self.db_name = db_name
            self.collection_name = collection_name
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
            self.data_dir = data_dir
            self.recall_threshold = recall_threshold
            self.topk = topk

    def load_config(self):
        config_dict = json.load()
        for key, value in config_dict.items():
            setattr(self, key, value)
            if not hasattr(self, key):
                print(f"Warning: {key} is not a valid attribute of Config class.")


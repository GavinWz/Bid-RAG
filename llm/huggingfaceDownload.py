# 1.安装huggingface_hub
# pip install huggingface_hub


import os

from huggingface_hub import snapshot_download

# print('downloading entire files...')
# # 注意，这种方式仍然保存在cache_dir中
# snapshot_download(repo_id="ibrahimhamamci/CT-RATE", repo_type="dataset",
#                   local_dir="本地路径",
#                   local_dir_use_symlinks=False, resume_download=True,
#                   token='hf_***')

# # 使用cache_dir参数，将模型/数据集保存到指定“本地路径”
# snapshot_download(repo_id="Qwen/Qwen2.5-7B-Instruct", repo_type="model",
#                   cache_dir="/root/models/llm",
#                   local_dir_use_symlinks=False, resume_download=True,
#                   token='')


# snapshot_download(repo_id="Qwen/Qwen2.5-7B-Instruct", cache_dir="/root/models/llm")


# download single file...，下载单个文件
# from huggingface_hub import hf_hub_download
# hf_hub_download(repo_id="ibrahimhamamci/CT-RATE", filename='config.json',
#                 repo_type="dataset",
#                 local_dir="/home/miao/data/dataset/CT-RATE/dataset/train",
#                 local_dir_use_symlinks=False, resume_download=True,
#                 force_download=False, subfolder='dataset/train/train_10006')



# from transformers import AutoTokenizer, AutoModelForMaskedLM
# tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct",cache_dir="/root/models/llm")
# model = AutoModelForMaskedLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct",cache_dir="/root/models/llm")


# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
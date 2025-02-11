import os
from vllm import LLM, SamplingParams

# 设置显存分配策略
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# 1. 定义模型路径或名称
model_name_or_path = "/root/models/glm4-9b-sft"  # 替换为你的模型路径

# 2. 加载模型，启用 trust_remote_code，设置 dtype 为 float16，并减少上下文长度
llm = LLM(
    model=model_name_or_path,
    trust_remote_code=True,
    dtype="float16",
    max_model_len=4096,  # 减少上下文长度
    # max_batch_size=4     # 减少批处理大小
    gpu_memory_utilization = 0.8 #为模型权重、激活值和 KV 缓存保留的 GPU 内存比率（介于 0 和 1 之间）。
    #较高的值将增加 KV 缓存大小，从而提高模型的吞吐量。但是，如果该值太高，可能会导致内存不足 (OOM) 错误。
)

# 3. 定义生成参数
sampling_params = SamplingParams(
    temperature=0.7,      # 控制随机性，值越高越随机
    top_p=0.9,            # Nucleus sampling，控制生成多样性
    max_tokens=500,       # 生成的最大 token 数
    n=2,                  # 生成多少个候选结果
    # stop=["\n", "###"],   # 停止生成的标记
    stop = []
)

# 4. 定义输入提示
prompts = [
    "国务院国资委在监督中央企业采购管理上有何角色？",
    "合肥市公共资源交易相关的规范性文件有哪些？",
    "交易平台如何开展招标文件见证工作并加强与监管联动？"
]

# 5. 生成文本
outputs = llm.generate(prompts, sampling_params)

# 6. 输出结果
for output in outputs:
    print(f"Prompt: {output.prompt}")
    print(f"Generated text: {output.outputs[0].text}")
    print("-" * 50)
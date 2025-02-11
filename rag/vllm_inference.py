from vllm import LLM

llm = LLM(
    model="/root/models/glm4-9b-pt",
    task="generate",
    trust_remote_code=True,
    dtype='float16',
    gpu_memory_utilization=0.8,
    max_model_len=40960
)

output = llm.generate("Hello, my name is")
print(output)

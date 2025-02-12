from openai import OpenAI
from vllm import LLM


def run():
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

def open_ai_generate(messages, api_key="dummy", base_url="http://localhost:7100/v1", stream=True):
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model="glm4-9b-pt",
        messages=messages,
        temperature=0.5,
        stream=True
    )
    if stream:
        for chunk in response:
            if chunk.choices is not None and len(chunk.choices) > 0:
                yield chunk.choices[0].delta.content
    else:
        return response.choices[0].message.content


if __name__ == '__main__':
    messages = [{"role": "user", "content": "Hello"}]
    result = open_ai_generate(messages)
    for s in result:
        print(s, end='')
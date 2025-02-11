import json
from rag.rag_answer import *
from rag.utils import load_everything
import re 

config, model, client, embedding_model = load_everything()

evaluate_dir = "/root/rag_project/data/test_qa_dir"

def read_eval_data(evaluate_dir):
    evaluate_data = []
    for file in os.listdir(evaluate_dir):
        if file.endswith(".json"):
            with open(os.path.join(evaluate_dir, file), "r") as f:
                qa_list = json.load(f)
                if len(qa_list) > 0:
                    # 获取文件对应的政策名字
                    file_name = re.search(r'^qa_([0-9]+\-)+(.*).txt.json$', file)[2]
                else: 
                    continue
                for qa in qa_list:
                    question = qa['messages'][1]['content']
                    evaluate_data.append((file_name, question))
    return evaluate_data
            

def evaluate(evaluate_data):
    correct = 0
    for policy, question in evaluate_data:
        print("=====================================")
        print(f"Policy: {policy}")
        print(f"Question: {question}")
        answers = recall(question, client, config, embedding_model, mute=True)

        recall_files = set()
        for answer in answers:
            file = answer.strip().splitlines()[0]
            file_name = re.search(r'^(.*)\(第[0-9]+段\)', file)[1]
            recall_files.add(file_name)
            print(f"Answer file: {file_name}")
            # print(f"Answer: {answer}")
            print("=====================================")
        if policy in recall_files:
            correct += 1

    print(f"Total: {len(evaluate_data)}")
    print(f"Correct: {correct}")
    print(f"Hits rate: {correct / len(evaluate_data)}")


evaluate_data = read_eval_data(evaluate_dir)
evaluate(evaluate_data)


'''

{{- if .Messages }}
{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}




{
  "System": "You are a helpful assistant.",
  "Tools": [
    {"Function": "get_weather"}
  ],
  "Messages": [
    {"Role": "user", "Content": "What is the weather in New York?"},
    {"Role": "assistant", "Content": ""},
    {"Role": "tool", "Content": "{\"temperature\": \"5°C\", \"condition\": \"Clear skies\"}"}
  ]
}


<|im_start|>system
You are a helpful assistant.
# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{"type": "function", "function": "get_weather"}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
<|im_end|>
<|im_start|>user
What is the weather in New York?<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "get_weather", "arguments": {"location": "New York"}}
</tool_call>
<|im_start|>user
<tool_response>
{"temperature": "5°C", "condition": "Clear skies"}
</tool_response><|im_end|>
<|im_start|>assistant
The weather in New York is currently 5°C with clear skies.<|im_end|>

'''
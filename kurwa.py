import torch
from transformers import DeepseekV2ForCausalLM, AutoTokenizer, GenerationConfig


# if torch.cuda.is_available():
#     print("CUDA")
#     device = torch.device("cuda")
# else:
#     print("CPU")
device = torch.device("cpu")

model = DeepseekV2ForCausalLM.from_pretrained("deepseek-ai/DeepSeek-V2-Lite", dtype=torch.bfloat16)
model.generation_config = GenerationConfig.from_pretrained("deepseek-ai/DeepSeek-V2-Lite")
model.generation_config.pad_token_id = model.generation_config.eos_token_id
model = model.to(device)
model.eval()

tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-V2-Lite")

question = input("Your question:\t")
messages = {"role": "assistant", "content": question}

input_tensor = tokenizer(question, return_tensors="pt").input_ids
with torch.no_grad():
    output_gen = model.generate(input_tensor, max_new_tokens=256)
#print(question)
answer = tokenizer.decode(output_gen[0][input_tensor.shape[1]:], skip_special_tokens=True)
print(answer)

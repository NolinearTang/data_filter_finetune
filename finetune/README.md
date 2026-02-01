# 实体对齐判断模型微调

使用 LLaMAFactory 微调 Qwen3 8B 模型，训练实体对齐判断任务。模型使用**思考模型**格式，将中间推理过程放在 `<think>` 标签中，最终答案为 "对齐" 或 "不对齐"。

---

## 目录结构

```
finetune/
├── README.md                          # 本文档
├── data/                              # 训练数据目录
│   └── entity_alignment_train.json    # 转换后的训练数据
├── configs/                           # 配置文件
│   ├── dataset_info.json              # LLaMAFactory 数据集配置
│   └── qwen3_8b_lora_sft.yaml         # 微调配置（LoRA SFT）
└── scripts/                           # 脚本
    ├── convert_to_llamafactory.py     # 数据格式转换脚本
    └── train.sh                       # 训练启动脚本
```

---

## 快速开始

### 1. 准备环境

#### 安装 LLaMAFactory

```bash
# 克隆 LLaMAFactory 仓库
git clone https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory

# 安装依赖
pip install -e ".[torch,metrics]"
```

#### 设置环境变量

```bash
export LLAMAFACTORY_PATH=/path/to/LLaMA-Factory
```

### 2. 转换数据格式

将 `data_processing/entity_alignment_filter.py` 的输出转换为 LLaMAFactory 训练格式：

```bash
cd finetune/scripts

# 合并对齐和不对齐数据并转换
python convert_to_llamafactory.py \
    --mode merge \
    --aligned ../../data_processing/filtered_aligned.json \
    --unaligned ../../data_processing/filtered_aligned_unaligned.json \
    --output ../data/entity_alignment_train.json \
    --include-unaligned
```

**参数说明**：
- `--mode`: 转换模式
  - `merge`: 合并对齐和不对齐数据
  - `single`: 只转换单个文件
- `--aligned`: 对齐数据文件路径
- `--unaligned`: 不对齐数据文件路径
- `--output`: 输出文件路径
- `--include-unaligned`: 是否包含不对齐的数据（推荐包含，提高模型判别能力）

### 3. 启动训练

```bash
cd finetune/scripts
chmod +x train.sh
./train.sh
```

或者直接使用 LLaMAFactory CLI：

```bash
cd LLaMA-Factory

llamafactory-cli train \
    --config_file ../finetune/configs/qwen3_8b_lora_sft.yaml \
    --dataset_dir ../finetune/data \
    --dataset_info ../finetune/configs/dataset_info.json
```

---

## 数据格式

### 输入格式（entity_alignment_filter 输出）

```json
{
  "question": "sv660n出现e100故障怎么办？",
  "chunk": "sv660系列变频器e100.1故障表示过电流...",
  "llm_analysis": "1. 提取question中的实体：产品信息-sv660n, 故障码信息-e100\n2. 提取chunk中的实体：产品信息-sv660, 故障码信息-e100.1\n3. 判断实体是否对齐：对齐\n4. 给出判断理由：sv660n和sv660主型号相同，e100和e100.1主码相同\n\n<label>对齐</label>"
}
```

### 输出格式（LLaMAFactory ShareGPT 训练格式）

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业的实体对齐检测助手。你的任务是判断question和chunk中的实体信息是否对齐。\n\n实体类型主要包括（但不限于）：\n1. 产品信息：产品型号、设备名称等（如：sv660n, sv660d, md500, is620p等）\n2. 故障码信息：各种形式的故障代码（如：e100, e100.1, err-01, fault_02, AL001等）\n3. 其他实体：参数名称、功能名称等\n\n对齐判断规则：\n\n【多实体对齐优先级规则】：\n1. **产品实体优先原则**：...\n2. **非产品实体的对齐规则**：...\n\n✓ 单个实体判定为【对齐】的情况：...\n✗ 单个实体判定为【不对齐】的情况：...\n⚠ 默认【对齐】（不过滤）的情况：..."
    },
    {
      "role": "user",
      "content": "请判断以下question和chunk中的实体是否对齐：\n\nQuestion: sv660n出现e100故障怎么办？\n\nChunk: sv660系列变频器e100.1故障表示过电流...\n\n请按以下格式回答：\n1. 提取question中的实体...\n2. 提取chunk中的实体...\n3. 判断实体是否对齐...\n4. 给出判断理由\n\n注意：...\n\n最后，请在标签中明确回答：<label>对齐</label> 或 <label>不对齐</label>"
    },
    {
      "role": "assistant",
      "content": "<think>\n1. 提取question中的实体：产品信息-sv660n, 故障码信息-e100\n2. 提取chunk中的实体：产品信息-sv660, 故障码信息-e100.1\n3. 判断实体是否对齐：对齐\n4. 给出判断理由：sv660n和sv660主型号相同，e100和e100.1主码相同\n</think>\n\n对齐"
    }
  ]
}
```

**关键点**：
- **ShareGPT messages 格式**：使用 `system/user/assistant` 三个角色
- **system 角色**：包含完整的系统提示词（规则、实体类型、对齐判断规则等），与推理时保持一致
- **user 角色**：包含完整的用户提示词模板（格式要求、注意事项等）
- **assistant 角色**：`<think>` 标签包裹推理过程 + 最终答案（"对齐" 或 "不对齐"）
- 这种格式确保**训练/推理提示词完全一致**，避免分布偏移
- 训练出的模型具有**思考能力**，类似 OpenAI o1

---

## 训练配置说明

### 模型配置（qwen3_8b_lora_sft.yaml）

```yaml
model_name_or_path: Qwen/Qwen3-8B-Instruct  # 基座模型
stage: sft                                     # 监督微调
finetuning_type: lora                          # LoRA 微调
lora_target: all                               # 对所有层应用 LoRA

dataset: entity_alignment_train                # 数据集名称（ShareGPT 格式）
template: qwen                                 # Qwen 模板
cutoff_len: 2048                               # 最大序列长度

per_device_train_batch_size: 2                 # 每设备批次大小
gradient_accumulation_steps: 8                 # 梯度累积步数
learning_rate: 5.0e-5                          # 学习率
num_train_epochs: 3.0                          # 训练轮数

val_size: 0.1                                  # 验证集比例
eval_steps: 500                                # 每500步评估一次
```

### 关键参数调整建议

| 参数 | 默认值 | 说明 | 调整建议 |
|------|--------|------|----------|
| `learning_rate` | 5e-5 | 学习率 | 数据量大可降至 3e-5 |
| `num_train_epochs` | 3 | 训练轮数 | 数据量小可增至 5-10 |
| `cutoff_len` | 2048 | 最大长度 | 根据实际数据调整 |
| `lora_rank` | 默认 | LoRA 秩 | 可添加 `lora_rank: 8` 减少参数 |
| `per_device_train_batch_size` | 2 | 批次大小 | 根据显存调整 |

---

## 训练后使用

### 1. 合并 LoRA 权重（可选）

```bash
llamafactory-cli export \
    --model_name_or_path Qwen/Qwen3-8B-Instruct \
    --adapter_name_or_path saves/qwen3-8b-entity-alignment \
    --template qwen \
    --finetuning_type lora \
    --export_dir models/qwen3-8b-entity-alignment-merged \
    --export_size 2 \
    --export_device cpu
```

### 2. 推理测试

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# 加载模型
model_path = "models/qwen3-8b-entity-alignment-merged"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="auto",
    torch_dtype="auto"
)

# 构造输入
question = "sv660n出现e100故障怎么办？"
chunk = "sv660系列变频器e100.1故障表示过电流..."

messages = [
    {"role": "system", "content": "你是一个实体对齐判断助手。"},
    {"role": "user", "content": f"判断以下question和chunk中的实体是否对齐\n\nQuestion: {question}\n\nChunk: {chunk}"}
]

text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

inputs = tokenizer([text], return_tensors="pt").to(model.device)

outputs = model.generate(
    **inputs,
    max_new_tokens=512,
    temperature=0.7
)

response = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
print(response)
```

**期望输出**：
```
<think>
1. 提取question中的实体：产品信息-sv660n, 故障码信息-e100
2. 提取chunk中的实体：产品信息-sv660, 故障码信息-e100.1
3. 判断实体是否对齐：对齐
4. 给出判断理由：产品主型号相同，故障码主码相同
</think>

对齐
```

### 3. 提取最终答案

```python
import re

def extract_final_answer(response: str) -> str:
    """提取 <think> 标签外的最终答案"""
    # 移除 <think> 标签及其内容
    answer = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
    return answer

final_answer = extract_final_answer(response)
print(f"最终判断: {final_answer}")  # 输出: 对齐
```

---

## 思考模型的优势

1. **可解释性强**：模型输出包含完整推理过程
2. **准确率高**：通过思考链提升复杂判断的准确性
3. **易于调试**：可以查看模型的推理步骤，发现问题
4. **适合微调**：较少的数据即可训练出高质量模型

---

## 常见问题

### Q1: 显存不足怎么办？

**方案1**：减小批次大小
```yaml
per_device_train_batch_size: 1
gradient_accumulation_steps: 16
```

**方案2**：使用量化训练
```yaml
quantization_bit: 4  # 4-bit 量化
```

**方案3**：使用 DeepSpeed ZeRO
```bash
deepspeed --num_gpus=2 train.py --config qwen3_8b_lora_sft.yaml --deepspeed ds_config.json
```

### Q2: 如何提高模型准确率？

1. **增加训练数据**：收集更多对齐/不对齐样本
2. **数据平衡**：确保对齐和不对齐样本比例合理（建议 1:1）
3. **增加训练轮数**：从 3 轮增加到 5-10 轮
4. **调整学习率**：尝试 3e-5 或 1e-4

### Q3: 如何在生产环境部署？

推荐使用 vLLM 或 TGI 进行高性能推理：

```bash
# 使用 vLLM
pip install vllm

python -m vllm.entrypoints.openai.api_server \
    --model models/qwen3-8b-entity-alignment-merged \
    --served-model-name entity-alignment \
    --port 8000
```

---

## 参考资源

- [LLaMAFactory 官方文档](https://github.com/hiyouga/LLaMA-Factory)
- [Qwen3 模型文档](https://github.com/QwenLM/Qwen)
- [LoRA 论文](https://arxiv.org/abs/2106.09685)
- [思考模型训练方法](https://openai.com/research/learning-to-reason-with-llms)

---

## 总结

通过本微调流程，你可以：
- ✅ 将 LLM 的推理过程转化为训练数据
- ✅ 训练一个具有思考能力的 Qwen3 8B 模型
- ✅ 在实体对齐判断任务上达到高准确率
- ✅ 获得可解释的模型输出

模型训练完成后，可以替代原来的大模型 API 调用，降低成本并提高推理速度。

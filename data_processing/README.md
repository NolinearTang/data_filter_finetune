# 数据处理模块使用文档

本模块包含数据清洗和实体对齐过滤功能，用于微调项目的数据预处理。

---

## 目录

1. [安装依赖](#安装依赖)
2. [数据清洗](#数据清洗)
3. [实体对齐过滤](#实体对齐过滤)
4. [多实体对齐规则详解](#多实体对齐规则详解)
5. [思考模型训练数据转换](#思考模型训练数据转换)
6. [输出示例](#输出示例)

---

## 安装依赖

```bash
pip install -r ../requirements.txt
```

---

## 数据清洗

### 功能说明

将Excel文件从宽格式（question + chunk1~chunk10）转换为长格式的question-chunk对。

### 输入数据格式

Excel文件应包含以下列：
- `question`: 问题文本
- `chunk1`, `chunk2`, ..., `chunk10`: 相关的文本块

### 使用方法

#### 方法1：直接运行脚本

修改 `data_cleaning.py` 中的文件路径后运行：

```python
if __name__ == '__main__':
    input_file = 'your_data.xlsx'  # 修改为你的输入文件路径
    output_file = 'output.json'     # 修改为你的输出文件路径
    convert_excel_to_question_chunk_pairs(input_file, output_file)
```

然后运行：
```bash
python data_cleaning.py
```

#### 方法2：作为模块导入使用

```python
from data_processing import convert_excel_to_question_chunk_pairs

# 调用函数
convert_excel_to_question_chunk_pairs('input.xlsx', 'output.json')
```

### 输出格式

输出为JSON列表格式：

```json
[
  {
    "question": "什么是AI?",
    "chunk": "AI是人工智能"
  },
  {
    "question": "什么是AI?",
    "chunk": "AI可以学习"
  }
]
```

---

## 实体对齐过滤

### 功能概述

检测question和chunk中的实体是否对齐，过滤出对齐的数据对用于微调。

### 实体类型

实体类型主要包括（但不限于）：

1. **产品信息**：产品型号、设备名称等
   - 例如：sv660n, sv660d, md500, is620p 等
2. **故障码信息**：各种形式的故障代码
   - 例如：e100, e100.1, err-01, fault_02, AL001 等
3. **其他实体**：参数名称、功能名称等

### 对齐规则

#### 【多实体对齐优先级规则】

##### 1. 产品实体优先原则（最高优先级）

- **如果question和chunk中都存在产品实体**：
  - 必须先判断产品实体是否对齐
  - 产品实体不对齐 → **直接判定为【不对齐】**，无需检查其他实体
  - 产品实体对齐 → 继续检查其他实体

**示例**：
- `sv660n + e100` ↔ `sv660d + e100` → **不对齐**（产品不对齐，即使故障码相同）
- `sv660n + e100` ↔ `sv660 + e100.1` → 对齐（产品对齐，继续检查其他实体）

##### 2. 非产品实体的对齐规则（当没有产品实体，或产品实体已对齐时）

- **如果存在多个其他类型的实体**（如故障码、参数等）：
  - **只要有至少一个实体对齐** → 判定为【对齐】
  - 所有实体都不对齐 → 判定为【不对齐】

**示例**：
- `e100 + p001` ↔ `e100.1 + p002` → **对齐**（e100和e100.1对齐，即使p001和p002不对齐）
- `e100 + p001` ↔ `e200 + p002` → **不对齐**（所有实体都不对齐）

#### ✓ 单个实体判定为【对齐】的情况

- 实体完全相同
- 产品型号：主型号相同，一个带后缀一个不带
  - 例如：`sv660n` ↔ `sv660` ✓
- 故障码：主码相同，一个带子码一个不带
  - 例如：`e100` ↔ `e100.1` ✓
- 实体之间有明确的上下级或包含关系

#### ✗ 单个实体判定为【不对齐】的情况

- 同类型但明确不同的产品型号
  - 例如：`sv660n` ↔ `sv660d` ✗（后缀字母不同）
- 同主码但不同子码的故障码
  - 例如：`e100.1` ↔ `e100.2` ✗（子码不同）
- 实体完全不相关

#### ⚠ 默认【对齐】（不过滤）的情况

- question中没有明确的实体信息
- chunk中没有明确的实体信息
- 无法确定实体是否对齐
- 存在疑问或不确定的情况

**重要原则**：当无法确定时，默认判定为【对齐】，避免误过滤有价值的数据。

### 使用方法

#### 1. 准备LLM对象

```python
# 你的LLM类需要实现do_llm方法
class YourLLM:
    def do_llm(self, user_input, system_input, system_prompt):
        # 调用大模型API
        # 返回模型响应文本
        return response_text
```

#### 2. 运行过滤脚本

**方法1：作为模块导入**

```python
from data_processing import filter_aligned_pairs

# 初始化你的LLM
llm = YourLLM()

# 执行过滤
filter_aligned_pairs(
    input_file='output.json',           # 输入文件
    output_file='filtered_aligned.json', # 输出文件
    llm=llm,                             # LLM对象
    batch_size=10                        # 每10条打印一次进度
)
```

**方法2：直接运行脚本**

修改 `entity_alignment_filter.py` 中的 `__main__` 部分，替换 `MockLLM` 为你的LLM实现，然后运行：

```bash
python entity_alignment_filter.py
```

#### 3. 输出文件

- `filtered_aligned.json`：对齐的数据（用于微调）
- `filtered_aligned_unaligned.json`：不对齐的数据（用于分析）

---

## 多实体对齐规则详解

### 规则总结表

| 产品实体 | 产品对齐 | 其他实体情况 | 最终判定 |
|---------|---------|------------|---------|
| 都存在 | ✗ 不对齐 | 任意 | **不对齐** |
| 都存在 | ✓ 对齐 | 至少一个对齐 | **对齐** |
| 都存在 | ✓ 对齐 | 全部不对齐 | **不对齐** |
| 不存在 | N/A | 至少一个对齐 | **对齐** |
| 不存在 | N/A | 全部不对齐 | **不对齐** |
| 不存在 | N/A | 无实体 | **对齐**（默认） |

### 典型场景示例

#### 场景1：产品实体不对齐（直接判定为不对齐）

```json
{
  "question": "sv660n出现e100故障怎么办？",
  "chunk": "sv660d变频器e100故障处理方法..."
}
```

**判定**：✗ 不对齐（产品sv660n和sv660d不对齐，即使故障码相同）

---

#### 场景2：产品实体对齐，其他实体部分对齐（判定为对齐）

```json
{
  "question": "sv660n的e100和p001参数如何设置？",
  "chunk": "sv660系列变频器e100.1故障和p002参数说明..."
}
```

**判定**：✓ 对齐（产品对齐，e100对齐，满足"至少一个对齐"）

---

#### 场景3：无产品实体，多个其他实体有一个对齐（判定为对齐）

```json
{
  "question": "e100和AL001报警如何处理？",
  "chunk": "e100.1故障和AL002报警的解决方案..."
}
```

**判定**：✓ 对齐（e100对齐，满足"至少一个对齐"）

---

#### 场景4：无产品实体，所有其他实体都不对齐（判定为不对齐）

```json
{
  "question": "e100.1和AL001报警如何处理？",
  "chunk": "e100.2故障和AL002报警的解决方案..."
}
```

**判定**：✗ 不对齐（所有实体都不对齐）

---

## 思考模型训练数据转换

### 概述

`llm_analysis` 字段包含了LLM的完整推理过程，非常适合用作思考模型（Thinking Model）的训练数据，类似于 OpenAI 的 o1 模型的思维链训练方式。

### 原始输出格式

```json
{
  "question": "sv660n出现e100故障怎么办？",
  "chunk": "sv660系列变频器e100.1故障表示过电流...",
  "llm_analysis": "1. 提取question中的实体：产品信息-sv660n, 故障码信息-e100\n2. 提取chunk中的实体：产品信息-sv660, 故障码信息-e100.1\n3. 判断实体是否对齐：对齐\n4. 给出判断理由：sv660n和sv660主型号相同\n\n<label>对齐</label>"
}
```

### 转换为思考模型训练格式

#### 方案1：使用 `<think>` 标签包裹推理过程

```json
{
  "question": "判断以下question和chunk的实体是否对齐：\n\nQuestion: sv660n出现e100故障怎么办？\nChunk: sv660系列变频器e100.1故障表示过电流...",
  "response": "<think>\n1. 提取question中的实体：产品信息-sv660n, 故障码信息-e100\n2. 提取chunk中的实体：产品信息-sv660, 故障码信息-e100.1\n3. 判断实体是否对齐：对齐\n4. 给出判断理由：sv660n和sv660主型号相同\n</think>\n\n<label>对齐</label>"
}
```

#### 方案2：分离思考过程和最终答案

```json
{
  "instruction": "判断question和chunk的实体是否对齐",
  "input": {
    "question": "sv660n出现e100故障怎么办？",
    "chunk": "sv660系列变频器e100.1故障表示过电流..."
  },
  "thinking": "1. 提取question中的实体...\n2. 提取chunk中的实体...",
  "output": "对齐"
}
```

### 转换脚本

```python
import json
import re

def convert_to_thinking_model_format(input_file: str, output_file: str, format_type: str = "think_tag"):
    """
    将实体对齐过滤结果转换为思考模型训练格式
    
    Args:
        input_file: 输入的aligned或unaligned JSON文件
        output_file: 输出的训练数据文件
        format_type: 格式类型，"think_tag" 或 "separated"
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    training_data = []
    
    for item in data:
        question = item['question']
        chunk = item['chunk']
        llm_analysis = item['llm_analysis']
        
        # 提取<label>标签中的内容
        label_match = re.search(r'<label>(.*?)</label>', llm_analysis)
        if label_match:
            label = label_match.group(1).strip()
            # 移除label部分，保留思考过程
            thinking = re.sub(r'\n*最后.*?<label>.*?</label>', '', llm_analysis).strip()
        else:
            continue
        
        if format_type == "think_tag":
            # 方案1：使用<think>标签
            training_item = {
                "question": f"判断以下question和chunk的实体是否对齐：\n\nQuestion: {question}\nChunk: {chunk}",
                "response": f"<think>\n{thinking}\n</think>\n\n<label>{label}</label>"
            }
        else:
            # 方案2：分离格式
            training_item = {
                "instruction": "判断question和chunk的实体是否对齐",
                "input": {
                    "question": question,
                    "chunk": chunk
                },
                "thinking": thinking,
                "output": label
            }
        
        training_data.append(training_item)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    print(f"已转换 {len(training_data)} 条数据到 {output_file}")
    return training_data


# 使用示例
if __name__ == '__main__':
    # 转换对齐的数据
    convert_to_thinking_model_format(
        'filtered_aligned.json',
        'thinking_model_train_aligned.json',
        format_type='think_tag'
    )
    
    # 转换不对齐的数据
    convert_to_thinking_model_format(
        'filtered_aligned_unaligned.json',
        'thinking_model_train_unaligned.json',
        format_type='think_tag'
    )
```

### 训练数据的优势

1. **包含完整推理过程**：不仅有答案，还有推理步骤
2. **结构化的思考流程**：提取实体 → 判断对齐 → 给出理由
3. **适合思考模型训练**：类似 OpenAI o1 的训练方式
4. **提高模型可解释性**：模型学会"思考后再回答"

### 使用场景

- **场景1**：训练专门的实体对齐判断模型，替代大模型API调用
- **场景2**：作为思考模型的训练样本，提升模型推理能力
- **场景3**：Few-shot 示例，在提示词中使用这些数据作为示例

---

## 输出示例

### 控制台输出

```
成功加载 3 条question-chunk对

开始处理 3 条数据...

处理第 1/3 条...
Question: sv660n出现e100故障怎么办？...
Chunk: sv660系列变频器e100.1故障表示过电流......
✓ 对齐

处理第 2/3 条...
Question: sv660n出现e100故障怎么办？...
Chunk: md500变频器e200故障处理方法......
✗ 不对齐

处理第 3/3 条...
Question: 如何设置参数？...
Chunk: 参数设置步骤：1. 进入菜单......
✓ 对齐

处理完成！
对齐数据: 2 条
不对齐数据: 1 条
对齐率: 66.67%

已保存对齐数据到: filtered_aligned.json
已保存不对齐数据到: filtered_aligned_unaligned.json
```

### 输出文件格式

**filtered_aligned.json**（对齐的数据，用于微调）

```json
[
  {
    "question": "sv660n出现e100故障怎么办？",
    "chunk": "sv660系列变频器e100.1故障表示过电流...",
    "llm_analysis": "1. 提取question中的实体：产品信息-sv660n, 故障码信息-e100\n2. 提取chunk中的实体：产品信息-sv660, 故障码信息-e100.1\n3. 判断：对齐\n4. 理由：主型号相同\n\n<label>对齐</label>"
  }
]
```

**filtered_aligned_unaligned.json**（不对齐的数据，用于分析）

```json
[
  {
    "question": "sv660n出现e100故障怎么办？",
    "chunk": "md500变频器e200故障处理方法...",
    "llm_analysis": "1. 提取question中的实体：产品-sv660n, 故障码-e100\n2. 提取chunk中的实体：产品-md500, 故障码-e200\n3. 判断：不对齐\n4. 理由：产品和故障码都不同\n\n<label>不对齐</label>"
  }
]
```

---

## 注意事项

1. **数据质量**：确保 `llm_analysis` 的质量，可以人工抽查和修正
2. **标签提取**：使用 `<label>` 标签可以准确提取最终答案
3. **思考过程**：`<think>` 标签内的内容是推理过程，不应该直接展示给用户
4. **平衡数据**：建议同时使用对齐和不对齐的数据进行训练
5. **产品实体优先**：在多实体场景中，产品实体的对齐性具有最高优先级

---

## 总结

通过本模块，你可以：
- ✓ 将Excel数据转换为question-chunk对
- ✓ 使用LLM进行实体对齐过滤
- ✓ 获得高质量的微调数据
- ✓ 生成思考模型训练数据
- ✓ 提高模型的推理能力和可解释性

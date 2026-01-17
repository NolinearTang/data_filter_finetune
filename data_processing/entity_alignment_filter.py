import json
import re
from typing import List, Dict


SYSTEM_PROMPT = """你是一个专业的实体对齐检测助手。你的任务是判断question和chunk中的实体信息是否对齐。

实体类型主要包括（但不限于）：
1. 产品信息：产品型号、设备名称等（如：sv660n, sv660d, md500, is620p等）
2. 故障码信息：各种形式的故障代码（如：e100, e100.1, err-01, fault_02, AL001等）
3. 其他实体：参数名称、功能名称等

对齐判断规则：

【多实体对齐优先级规则】：
1. **产品实体优先原则**：
   - 如果question和chunk中都存在产品实体，必须先判断产品实体是否对齐
   - 产品实体不对齐 → 直接判定为【不对齐】，无需检查其他实体
   - 产品实体对齐 → 继续检查其他实体

2. **非产品实体的对齐规则**（当没有产品实体，或产品实体已对齐时）：
   - 如果存在多个其他类型的实体（如故障码、参数等）
   - 只要有至少一个实体对齐 → 判定为【对齐】
   - 所有实体都不对齐 → 判定为【不对齐】

✓ 单个实体判定为【对齐】的情况：
  - 实体完全相同
  - 产品型号：主型号相同，一个带后缀一个不带（如：sv660n ↔ sv660）
  - 故障码：主码相同，一个带子码一个不带（如：e100 ↔ e100.1）
  - 实体之间有明确的上下级或包含关系

✗ 单个实体判定为【不对齐】的情况：
  - 同类型但明确不同的产品型号（如：sv660n ↔ sv660d，后缀字母不同）
  - 同主码但不同子码的故障码（如：e100.1 ↔ e100.2，子码不同）
  - 实体完全不相关

⚠ 默认【对齐】（不过滤）的情况：
  - question中没有明确的实体信息
  - chunk中没有明确的实体信息
  - 无法确定实体是否对齐
  - 存在疑问或不确定的情况

重要原则：当无法确定时，默认判定为【对齐】，避免误过滤有价值的数据。"""


USER_PROMPT_TEMPLATE = """请判断以下question和chunk中的实体是否对齐：

Question: {question}

Chunk: {chunk}

请按以下格式回答：
1. 提取question中的实体（分别列出：产品信息、故障码信息、其他实体，如果没有则说明"无明确实体"）
2. 提取chunk中的实体（分别列出：产品信息、故障码信息、其他实体，如果没有则说明"无明确实体"）
3. 判断实体是否对齐：
   - 如果存在产品实体，先判断产品实体是否对齐（产品实体不对齐则直接判定为不对齐）
   - 如果产品实体对齐或不存在产品实体，判断其他实体（多个实体只要有一个对齐即可）
4. 给出判断理由

注意：
- 产品实体优先：如果双方都有产品实体但不对齐，直接判定为"不对齐"
- 其他实体宽松：如果有多个非产品实体，只要有一个对齐就判定为"对齐"
- 如果question或chunk中没有明确实体，或者无法确定是否对齐，请判定为"对齐"

最后，请在标签中明确回答：<label>对齐</label> 或 <label>不对齐</label>"""


def load_question_chunk_pairs(json_file: str) -> List[Dict]:
    """
    加载question-chunk对的JSON文件
    
    Args:
        json_file: JSON文件路径
        
    Returns:
        question-chunk对的列表
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"成功加载 {len(data)} 条question-chunk对")
    return data


def check_entity_alignment(question: str, chunk: str, llm) -> Dict:
    """
    使用LLM检查question和chunk的实体对齐情况
    
    Args:
        question: 问题文本
        chunk: 文本块
        llm: LLM对象，需要有do_llm方法
        
    Returns:
        包含对齐结果的字典
    """
    user_input = USER_PROMPT_TEMPLATE.format(
        question=question,
        chunk=chunk
    )
    
    system_input = ""
    
    response = llm.do_llm(
        user_input=user_input,
        system_input=system_input,
        system_prompt=SYSTEM_PROMPT
    )
    
    # 使用正则表达式提取<label>标签中的内容
    label_match = re.search(r'<label>(.*?)</label>', response)
    if label_match:
        label_content = label_match.group(1).strip()
        is_aligned = label_content == "对齐"
    else:
        # 如果没有找到标签，使用原来的方法作为后备
        is_aligned = "对齐" in response and "不对齐" not in response
    
    return {
        'question': question,
        'chunk': chunk,
        'llm_response': response,
        'is_aligned': is_aligned
    }


def filter_aligned_pairs(input_file: str, output_file: str, llm, batch_size: int = 10):
    """
    过滤出实体对齐的question-chunk对
    
    Args:
        input_file: 输入JSON文件路径
        output_file: 输出JSON文件路径
        llm: LLM对象
        batch_size: 每处理多少条数据保存一次
    """
    data = load_question_chunk_pairs(input_file)
    
    aligned_pairs = []
    unaligned_pairs = []
    
    print(f"\n开始处理 {len(data)} 条数据...")
    
    for idx, pair in enumerate(data):
        question = pair['question']
        chunk = pair['chunk']
        
        print(f"\n处理第 {idx + 1}/{len(data)} 条...")
        print(f"Question: {question[:50]}...")
        print(f"Chunk: {chunk[:50]}...")
        
        try:
            result = check_entity_alignment(question, chunk, llm)
            
            if result['is_aligned']:
                aligned_pairs.append({
                    'question': question,
                    'chunk': chunk,
                    'llm_analysis': result['llm_response']
                })
                print("✓ 对齐")
            else:
                unaligned_pairs.append({
                    'question': question,
                    'chunk': chunk,
                    'llm_analysis': result['llm_response']
                })
                print("✗ 不对齐")
            
            if (idx + 1) % batch_size == 0:
                print(f"\n已处理 {idx + 1} 条，当前对齐: {len(aligned_pairs)}, 不对齐: {len(unaligned_pairs)}")
                
        except Exception as e:
            print(f"处理出错: {e}")
            unaligned_pairs.append({
                'question': question,
                'chunk': chunk,
                'error': str(e)
            })
    
    print(f"\n处理完成！")
    print(f"对齐数据: {len(aligned_pairs)} 条")
    print(f"不对齐数据: {len(unaligned_pairs)} 条")
    print(f"对齐率: {len(aligned_pairs) / len(data) * 100:.2f}%")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(aligned_pairs, f, ensure_ascii=False, indent=2)
    print(f"\n已保存对齐数据到: {output_file}")
    
    unaligned_file = output_file.replace('.json', '_unaligned.json')
    with open(unaligned_file, 'w', encoding='utf-8') as f:
        json.dump(unaligned_pairs, f, ensure_ascii=False, indent=2)
    print(f"已保存不对齐数据到: {unaligned_file}")
    
    return aligned_pairs, unaligned_pairs


if __name__ == '__main__':
    class MockLLM:
        """示例LLM类，实际使用时替换为真实的LLM"""
        def do_llm(self, user_input, system_input, system_prompt):
            return "示例响应：对齐"
    
    llm = MockLLM()
    
    input_file = 'output.json'
    output_file = 'filtered_aligned.json'
    
    filter_aligned_pairs(input_file, output_file, llm)

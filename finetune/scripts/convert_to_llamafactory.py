"""
将 entity_alignment_filter 的输出转换为 LLaMAFactory 训练格式（ShareGPT）

输入格式（entity_alignment_filter 输出）：
{
  "question": "...",
  "chunk": "...",
  "llm_analysis": "1. 提取question中的实体...\n2. 提取chunk中的实体...\n3. 判断...\n4. 理由...\n\n<label>对齐</label>"
}

输出格式（ShareGPT messages 格式，支持思考模型）：
{
  "messages": [
    {"role": "system", "content": "完整的系统提示词..."},
    {"role": "user", "content": "请判断以下question和chunk中的实体是否对齐：\n\nQuestion: ...\n\nChunk: ..."},
    {"role": "assistant", "content": "<think>\n推理过程...\n</think>\n\n对齐"}
  ]
}
"""

import json
import re
import sys
import os
from typing import List, Dict
import argparse

# 添加 data_processing 到路径以导入 SYSTEM_PROMPT
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../data_processing'))
from entity_alignment_filter import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def extract_label_and_thinking(llm_analysis: str) -> tuple:
    """
    从 llm_analysis 中提取 label 和 thinking 内容
    
    Args:
        llm_analysis: LLM 的完整分析文本
        
    Returns:
        (thinking_content, label_content) 元组
    """
    # 提取 <label> 标签中的内容
    label_match = re.search(r'<label>(.*?)</label>', llm_analysis, re.DOTALL)
    if label_match:
        label = label_match.group(1).strip()
        # 移除 label 部分，剩余的就是 thinking 内容
        thinking = re.sub(r'\n*<label>.*?</label>\s*$', '', llm_analysis, flags=re.DOTALL).strip()
    else:
        # 如果没有 label 标签，尝试从文本末尾提取
        if llm_analysis.endswith('对齐') or llm_analysis.endswith('不对齐'):
            lines = llm_analysis.strip().split('\n')
            label = lines[-1].strip()
            thinking = '\n'.join(lines[:-1]).strip()
        else:
            # 默认情况
            label = "对齐"
            thinking = llm_analysis.strip()
    
    return thinking, label


def convert_to_llamafactory_format(
    input_file: str,
    output_file: str,
    dataset_name: str = "entity_alignment"
):
    """
    转换数据格式为 ShareGPT messages 格式
    
    Args:
        input_file: 输入的 JSON 文件（entity_alignment_filter 输出）
        output_file: 输出的 JSON 文件（LLaMAFactory ShareGPT 格式）
        dataset_name: 数据集名称
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    converted_data = []
    
    for idx, item in enumerate(data):
        question = item['question']
        chunk = item['chunk']
        llm_analysis = item.get('llm_analysis', '')
        
        # 提取 thinking 和 label
        thinking, label = extract_label_and_thinking(llm_analysis)
        
        # 构造用户输入（使用原始的 USER_PROMPT_TEMPLATE 格式）
        user_content = USER_PROMPT_TEMPLATE.format(question=question, chunk=chunk)
        
        # 构造助手输出（<think> + 最终答案）
        assistant_content = f"<think>\n{thinking}\n</think>\n\n{label}"
        
        # 构造 ShareGPT messages 格式
        converted_item = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content}
            ]
        }
        
        converted_data.append(converted_item)
    
    # 保存转换后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
    
    print(f"转换完成！")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print(f"总条数: {len(converted_data)}")
    print(f"\n示例数据（第1条）：")
    if converted_data:
        print(json.dumps(converted_data[0], ensure_ascii=False, indent=2))


def merge_and_convert(
    aligned_file: str,
    unaligned_file: str,
    output_file: str,
    include_unaligned: bool = True
):
    """
    合并对齐和不对齐的数据，并转换格式
    
    Args:
        aligned_file: 对齐数据文件
        unaligned_file: 不对齐数据文件
        output_file: 输出文件
        include_unaligned: 是否包含不对齐的数据
    """
    all_data = []
    
    # 加载对齐数据
    with open(aligned_file, 'r', encoding='utf-8') as f:
        aligned_data = json.load(f)
        all_data.extend(aligned_data)
    
    print(f"加载对齐数据: {len(aligned_data)} 条")
    
    # 加载不对齐数据（可选）
    if include_unaligned:
        try:
            with open(unaligned_file, 'r', encoding='utf-8') as f:
                unaligned_data = json.load(f)
                all_data.extend(unaligned_data)
            print(f"加载不对齐数据: {len(unaligned_data)} 条")
        except FileNotFoundError:
            print(f"未找到不对齐数据文件: {unaligned_file}")
    
    print(f"总数据量: {len(all_data)} 条")
    
    # 转换格式为 ShareGPT messages
    converted_data = []
    for item in all_data:
        question = item['question']
        chunk = item['chunk']
        llm_analysis = item.get('llm_analysis', '')
        
        # 跳过有错误的数据
        if 'error' in item:
            continue
        
        thinking, label = extract_label_and_thinking(llm_analysis)
        
        # 构造用户输入
        user_content = USER_PROMPT_TEMPLATE.format(question=question, chunk=chunk)
        
        # 构造助手输出
        assistant_content = f"<think>\n{thinking}\n</think>\n\n{label}"
        
        # ShareGPT messages 格式
        converted_item = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content}
            ]
        }
        
        converted_data.append(converted_item)
    
    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n转换完成！")
    print(f"输出文件: {output_file}")
    print(f"有效数据: {len(converted_data)} 条")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='转换数据为 LLaMAFactory 格式')
    parser.add_argument('--mode', type=str, choices=['single', 'merge'], default='merge',
                        help='转换模式: single(单文件) 或 merge(合并对齐+不对齐)')
    parser.add_argument('--input', type=str, help='输入文件路径（single模式）')
    parser.add_argument('--aligned', type=str, 
                        default='../data_processing/filtered_aligned.json',
                        help='对齐数据文件路径（merge模式）')
    parser.add_argument('--unaligned', type=str,
                        default='../data_processing/filtered_aligned_unaligned.json',
                        help='不对齐数据文件路径（merge模式）')
    parser.add_argument('--output', type=str, 
                        default='../finetune/data/entity_alignment_train.json',
                        help='输出文件路径')
    parser.add_argument('--include-unaligned', action='store_true', default=True,
                        help='是否包含不对齐的数据')
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        if not args.input:
            print("错误: single 模式需要指定 --input 参数")
            exit(1)
        convert_to_llamafactory_format(args.input, args.output)
    else:
        merge_and_convert(
            args.aligned,
            args.unaligned,
            args.output,
            args.include_unaligned
        )

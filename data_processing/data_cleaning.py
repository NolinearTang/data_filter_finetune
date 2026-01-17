import pandas as pd
import json


def convert_excel_to_question_chunk_pairs(input_file, output_file):
    """
    将Excel文件从宽格式转换为长格式的question-chunk对
    
    Args:
        input_file: 输入Excel文件路径
        output_file: 输出JSON文件路径
    """
    df = pd.read_excel(input_file)
    
    print(f"读取Excel文件: {input_file}")
    print(f"原始数据形状: {df.shape}")
    print(f"列名: {df.columns.tolist()}")
    
    question_chunk_pairs = []
    
    for idx, row in df.iterrows():
        question = row['question']
        
        if pd.isna(question) or str(question).strip() == '':
            print(f"警告: 第{idx+2}行的question为空，跳过该行")
            continue
        
        for i in range(1, 11):
            chunk_col = f'chunk{i}'
            
            if chunk_col not in df.columns:
                print(f"警告: 列 {chunk_col} 不存在")
                break
            
            chunk_value = row[chunk_col]
            
            if pd.isna(chunk_value) or str(chunk_value).strip() == '':
                break
            
            question_chunk_pairs.append({
                'question': str(question).strip(),
                'chunk': str(chunk_value).strip()
            })
    
    print(f"\n转换完成!")
    print(f"生成的question-chunk对数量: {len(question_chunk_pairs)}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(question_chunk_pairs, f, ensure_ascii=False, indent=2)
    
    print(f"已保存为JSON文件: {output_file}")
    
    if len(question_chunk_pairs) > 0:
        print(f"\n前5条数据预览:")
        for i, pair in enumerate(question_chunk_pairs[:5]):
            print(f"{i+1}. Question: {pair['question'][:50]}...")
            print(f"   Chunk: {pair['chunk'][:50]}...")
    
    return question_chunk_pairs


if __name__ == '__main__':
    input_file = 'input.xlsx'
    output_file = 'output.json'
    convert_excel_to_question_chunk_pairs(input_file, output_file)

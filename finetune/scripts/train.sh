#!/bin/bash

# LLaMAFactory 微调脚本 - Qwen3 8B LoRA SFT
# 使用思考模型格式训练实体对齐判断任务

# 设置 LLaMAFactory 路径（请根据实际情况修改）
LLAMAFACTORY_PATH=${LLAMAFACTORY_PATH:-"LLaMA-Factory"}

# 检查 LLaMAFactory 是否存在
if [ ! -d "$LLAMAFACTORY_PATH" ]; then
    echo "错误: 未找到 LLaMAFactory，请先克隆仓库："
    echo "git clone https://github.com/hiyouga/LLaMA-Factory.git"
    echo "或设置环境变量: export LLAMAFACTORY_PATH=/path/to/LLaMA-Factory"
    exit 1
fi

# 进入 LLaMAFactory 目录
cd "$LLAMAFACTORY_PATH" || exit 1

# 设置数据集路径
export DATA_DIR="$(dirname "$(dirname "$(pwd)")")/finetune/data"
export DATASET_INFO="$(dirname "$(dirname "$(pwd)")")/finetune/configs/dataset_info.json"

echo "数据目录: $DATA_DIR"
echo "数据集配置: $DATASET_INFO"

# 运行训练
llamafactory-cli train \
    --config_file "$(dirname "$(dirname "$(pwd)")")/finetune/configs/qwen3_8b_lora_sft.yaml" \
    --dataset_dir "$DATA_DIR" \
    --dataset_info "$DATASET_INFO"

echo "训练完成！"
echo "模型保存在: saves/qwen3-8b-entity-alignment"

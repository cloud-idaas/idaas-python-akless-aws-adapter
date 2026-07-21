#!/bin/zsh
# 运行 IDaaS PAM AWS S3 示例脚本
# 用法：
#   export IDAAS_CLIENT_SECRET="你的客户端密钥"
#   ./run_sample.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SAMPLE_FILE="$SCRIPT_DIR/samples/aws_s3_sample.py"

if [ ! -d "$VENV_DIR" ]; then
    echo "错误：虚拟环境不存在，请先创建并激活 .venv"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -e \".[boto3,dev]\""
    exit 1
fi

if [ -z "$IDAAS_CLIENT_SECRET" ]; then
    echo "错误：未设置 IDAAS_CLIENT_SECRET 环境变量"
    echo "请先执行："
    echo "  export IDAAS_CLIENT_SECRET=\"你的客户端密钥\""
    exit 1
fi

echo "激活虚拟环境..."
source "$VENV_DIR/bin/activate"

echo "运行示例：$SAMPLE_FILE"
python "$SAMPLE_FILE"

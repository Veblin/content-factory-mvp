"""配置加载 — 从 .env 读取环境变量"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env
load_dotenv(Path(__file__).parent / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

OUTPUT_DIR = Path(__file__).parent / "output"
DATA_DIR = Path(__file__).parent / "data"

# 确保输出目录存在
OUTPUT_DIR.mkdir(exist_ok=True)

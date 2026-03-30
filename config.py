"""配置加载 — 从 .env 读取环境变量"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env
load_dotenv(Path(__file__).parent / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

SCOUT_MODEL = os.getenv("SCOUT_MODEL", "deepseek-chat")
STRATEGIST_MODEL = os.getenv("STRATEGIST_MODEL", "deepseek-chat")
RESONANCE_MODEL = os.getenv("RESONANCE_MODEL", "deepseek-chat")
EVIDENCE_MODEL = os.getenv("EVIDENCE_MODEL", "deepseek-chat")
WRITER_MODEL = os.getenv("WRITER_MODEL", "deepseek-chat")
ART_DIRECTOR_MODEL = os.getenv("ART_DIRECTOR_MODEL", "deepseek-chat")

OUTPUT_DIR = Path(__file__).parent / "output"
DATA_DIR = Path(__file__).parent / "data"

# 确保输出目录存在
OUTPUT_DIR.mkdir(exist_ok=True)

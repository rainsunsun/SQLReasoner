"""pytest 公共配置：保证无论从哪个目录运行都能 import app 包。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

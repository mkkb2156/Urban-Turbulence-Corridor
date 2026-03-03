"""Vercel Serverless Function 入口。

Vercel 會自動偵測此檔案並作為 /api/* 的 handler。
"""

import sys
from pathlib import Path

# 加入專案根目錄至 Python path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.api.main import app  # noqa: E402, F401

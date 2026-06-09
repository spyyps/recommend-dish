#!/usr/bin/env python3
"""菜单 MCP server 入口（开发/源码运行使用）。

发布后用户走 `menus-mcp` 命令；本脚本仅为在仓库 clone 后无需 pip install 直接运行。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from menus_mcp import main  # noqa: E402

if __name__ == "__main__":
    main()

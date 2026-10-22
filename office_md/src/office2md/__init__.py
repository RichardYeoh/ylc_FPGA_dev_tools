# -*- coding: utf-8 -*-
"""Office 文档转 Markdown —— 主包。

设计要点（详见 docs/软件设计书.md）：
- 主干全部使用纯 Python 的 OOXML 解析库，不依赖外部进程、不联网。
- 老格式 .doc/.ppt 通过本机已安装的 Microsoft Office COM 接口另存为新格式后再解析。
- 所有路径解析基于程序自身所在目录，保证整目录拷贝即可迁移。
"""

__version__ = "1.0.0"
__app_name__ = "office_md"

# 支持转换的扩展名 -> 内部类型
EXT_MAP = {
    ".docx": "docx",
    ".docm": "docx",
    ".doc": "doc",
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".xls": "xls",
    ".pptx": "pptx",
    ".pptm": "pptx",
    ".ppt": "ppt",
}

# 文件选择框用的过滤器
FILE_PATTERNS = "*.doc;*.docx;*.docm;*.xls;*.xlsx;*.xlsm;*.ppt;*.pptx;*.pptm"

SUPPORTED_EXTS = tuple(EXT_MAP.keys())

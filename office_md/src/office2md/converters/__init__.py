# -*- coding: utf-8 -*-
"""各格式转换器集合。

每个 converter 模块导出形如 `convert_xxx(src, md_path, options) -> (markdown, warnings)`
的函数，由 core.convert_one 统一调度。
"""

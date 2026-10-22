# -*- coding: utf-8 -*-
"""支持 `python -m office2md` 方式启动。"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重明鸟智能体 - 全量新闻媒体爬虫系统统一主入口 (Main Entrypoint)
直接转发并调用 unified_crawler.main()
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from unified_crawler import main

if __name__ == "__main__":
    main()

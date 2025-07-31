#!/usr/bin/env python3
"""
Dev Peace - Observador inteligente de desenvolvimento que gera worklogs automaticamente.

Ponto de entrada principal do aplicativo.
"""

import sys
from src.dev_peace.cli.main import main

if __name__ == "__main__":
    sys.exit(main())

"""Ponto de entrada usado pelo PyInstaller (executável Rio Dashboard)."""
import sys

from rio_dashboard.principal import main

if __name__ == "__main__":
    main(sys.argv[1:])

"""
main.py — Ponto de entrada do Gerador Inteligente de Documentos.

Execute com: python main.py
"""
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import MainWindow


def _recurso(relativo: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativo)


def _aplicar_icone(app: QApplication):
    ico = _recurso("logo.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _aplicar_icone(app)

    janela = MainWindow()
    janela.show()
    janela.verificar_atualizacoes()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

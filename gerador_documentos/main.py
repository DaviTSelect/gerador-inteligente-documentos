"""
main.py — Ponto de entrada do Gerador Inteligente de Documentos.

Execute com: python main.py
"""
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import updater
from app import MainWindow


def _recurso(relativo: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativo)


def _aplicar_icone(app: QApplication):
    ico = _recurso("logo.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))


def _verificar_instalacao(versao_esperada: str = "") -> int:
    """
    Usado pelo atualizador antes de instalar um novo .exe: confirma que ele
    abre e que o essencial funciona (importações, Qt, .docx, version.txt).
    """
    import io

    import win32com.client  # noqa: F401
    from docx import Document

    QApplication(sys.argv)
    Document().save(io.BytesIO())
    versao = updater.versao_para_tupla(updater.ler_versao_local())
    if versao in (None, (0, 0, 0, 0)):
        return 1
    # Um build de versão diferente da release causaria atualização em loop
    if versao_esperada and versao != updater.versao_para_tupla(versao_esperada):
        updater.log.error("Versão do executável difere da release %s", versao_esperada)
        return 1
    return 0


def main():
    verificar = [a for a in sys.argv[1:] if a.startswith(updater.ARG_VERIFICAR)]
    if verificar:
        updater.configurar_log()
        try:
            codigo = _verificar_instalacao(verificar[0].partition("=")[2])
        except Exception:
            updater.log.exception("Autoverificação falhou")
            codigo = 1
        sys.exit(codigo)

    updater.configurar_log()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _aplicar_icone(app)

    janela = MainWindow()
    janela.show()
    janela.verificar_atualizacoes()
    # O backup da versão anterior só é apagado depois que esta abriu e se manteve
    QTimer.singleShot(15000, updater.limpar_residuos)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
main.py — Ponto de entrada do Gerador Inteligente de Documentos.

Execute com: python main.py
"""
import os
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QLabel,
    QMessageBox, QProgressBar, QVBoxLayout,
)

from app import MainWindow


# ── Recurso path (funciona em dev e em .exe compilado) ───────────────────────

def _recurso(relativo: str) -> str:
    """Resolve caminho de arquivo recurso para dev e para exe PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativo)


# ── Ícone da aplicação ────────────────────────────────────────────────────────

def _aplicar_icone(app: QApplication):
    ico = _recurso("logo.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))


# ── Thread de verificação de atualização ─────────────────────────────────────

class _ThreadVerificacao(QThread):
    resultado = Signal(dict)

    def run(self):
        try:
            import updater
            info = updater.verificar_atualizacao()
        except Exception:
            info = {"disponivel": False}
        self.resultado.emit(info)


# ── Dialog de progresso de download ──────────────────────────────────────────

class _DialogProgresso(QDialog):
    def __init__(self, versao: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Atualizando…")
        self.setFixedSize(360, 120)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        self.label = QLabel(f"Baixando versão {versao}…")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(0)
        layout.addWidget(self.barra)

    def atualizar(self, baixados: int, total: int):
        if total > 0:
            self.barra.setValue(int(baixados / total * 100))
            self.barra.setFormat(
                f"{baixados // 1024} KB / {total // 1024} KB"
            )
        else:
            self.barra.setRange(0, 0)  # indeterminado
        QApplication.processEvents()


class _ThreadDownload(QThread):
    progresso = Signal(int, int)
    concluido = Signal(bool)

    def __init__(self, url: str, versao: str):
        super().__init__()
        self._url = url
        self._versao = versao

    def run(self):
        try:
            import updater
            updater.aplicar_atualizacao(
                self._url, self._versao,
                callback_progresso=lambda b, t: self.progresso.emit(b, t),
            )
            self.concluido.emit(True)
        except Exception:
            self.concluido.emit(False)


# ── Verificação de atualizações (executado antes da janela principal) ─────────

def _verificar_atualizacoes(app: QApplication):
    """
    Verifica atualizações em background.
    Se houver, pergunta ao usuário; se confirmar, baixa, aplica e reinicia.
    """
    # Roda verificação em thread para não travar o splash/início
    thread = _ThreadVerificacao()
    info_resultado = {}

    def _ao_concluir(info: dict):
        info_resultado.update(info)
        loop.quit()

    thread.resultado.connect(_ao_concluir)
    thread.start()

    # Mini event-loop que espera a thread (máx. ~8s pelo timeout interno)
    from PySide6.QtCore import QEventLoop
    loop = QEventLoop()
    thread.resultado.connect(loop.quit)
    loop.exec()

    if not info_resultado.get("disponivel"):
        return

    versao_nova = info_resultado["versao_nova"]
    versao_local = info_resultado["versao_local"]
    url = info_resultado["url_download"]
    notas = info_resultado.get("notas", "")

    msg = QMessageBox()
    msg.setWindowTitle("Atualização disponível")
    msg.setIcon(QMessageBox.Information)
    msg.setText(
        f"<b>Nova versão disponível: v{versao_nova}</b><br>"
        f"Versão atual: v{versao_local}"
    )
    if notas:
        msg.setInformativeText(notas[:400])
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes)
    msg.button(QMessageBox.Yes).setText("Atualizar agora")
    msg.button(QMessageBox.No).setText("Depois")

    if msg.exec() != QMessageBox.Yes:
        return

    # Download com progresso
    dialogo = _DialogProgresso(versao_nova)
    dialogo.show()

    thread_dl = _ThreadDownload(url, versao_nova)
    thread_dl.progresso.connect(dialogo.atualizar)

    concluiu = [False]

    def _dl_concluido(ok: bool):
        concluiu[0] = ok
        loop2.quit()

    thread_dl.concluido.connect(_dl_concluido)
    thread_dl.start()

    from PySide6.QtCore import QEventLoop
    loop2 = QEventLoop()
    thread_dl.concluido.connect(loop2.quit)
    loop2.exec()

    dialogo.close()

    if concluiu[0]:
        QMessageBox.information(
            None,
            "Atualizado!",
            f"Versão {versao_nova} instalada.\nO aplicativo será reiniciado.",
        )
        import updater
        updater.reiniciar()
    else:
        QMessageBox.warning(
            None,
            "Falha na atualização",
            "Não foi possível baixar a atualização.\nTente novamente mais tarde.",
        )


# ── Ponto de entrada ──────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    _aplicar_icone(app)
    _verificar_atualizacoes(app)

    janela = MainWindow()
    janela.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

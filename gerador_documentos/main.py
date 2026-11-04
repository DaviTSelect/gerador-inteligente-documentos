"""
main.py — Ponto de entrada do Gerador Inteligente de Documentos.

Execute com: python main.py
"""
import os
import sys

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QFont, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QMessageBox,
    QProgressBar, QVBoxLayout, QHBoxLayout, QWidget, QFrame,
)

from app import MainWindow


# ── Recurso path (funciona em dev e em .exe compilado) ───────────────────────

def _recurso(relativo: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativo)


# ── Versão local ──────────────────────────────────────────────────────────────

def _ler_versao() -> str:
    try:
        with open(_recurso("version.txt"), "r", encoding="utf-8") as f:
            return f.read().strip().lstrip("v")
    except Exception:
        return "?"


# ── Ícone da aplicação ────────────────────────────────────────────────────────

def _aplicar_icone(app: QApplication):
    ico = _recurso("logo.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))


# ── Tela de Splash ────────────────────────────────────────────────────────────

class SplashScreen(QWidget):
    """Tela de abertura que exibe o status da verificação de atualizações."""

    def __init__(self, versao: str):
        super().__init__()
        self._versao = versao
        self._dots = 0
        self._animando = False

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(480, 280)

        self._setup_ui()
        self._centralizar()

    def _setup_ui(self):
        self.setStyleSheet("""
            SplashScreen {
                background: #0F172A;
                border: 1px solid #1E2D3D;
            }
        """)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(40, 36, 40, 32)
        raiz.setSpacing(0)

        # ── Logo + nome ───────────────────────────────────────────────────────
        topo = QHBoxLayout()
        topo.setSpacing(14)

        ico_path = _recurso("logo.ico")
        if os.path.exists(ico_path):
            from PySide6.QtGui import QPixmap
            icone_label = QLabel()
            px = QPixmap(ico_path).scaled(
                48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            icone_label.setPixmap(px)
            icone_label.setFixedSize(48, 48)
            topo.addWidget(icone_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        nome_label = QLabel("Gerador Inteligente de Documentos")
        nome_label.setStyleSheet("color: #E2E8F0; font-size: 15px; font-weight: 600;")
        info_col.addWidget(nome_label)

        self._label_versao = QLabel(f"v{self._versao}")
        self._label_versao.setStyleSheet("color: #64748B; font-size: 12px;")
        info_col.addWidget(self._label_versao)

        topo.addLayout(info_col)
        topo.addStretch()
        raiz.addLayout(topo)

        # ── Separador ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #1E2D3D; border: none; min-height: 1px; max-height: 1px;")
        raiz.addSpacing(24)
        raiz.addWidget(sep)
        raiz.addSpacing(24)

        # ── Área de status ────────────────────────────────────────────────────
        raiz.addStretch()

        self._label_status = QLabel("Verificando atualizações...")
        self._label_status.setAlignment(Qt.AlignCenter)
        self._label_status.setStyleSheet(
            "color: #94A3B8; font-size: 13px;"
        )
        raiz.addWidget(self._label_status)

        raiz.addSpacing(14)

        self._barra = QProgressBar()
        self._barra.setRange(0, 0)  # indeterminado
        self._barra.setFixedHeight(3)
        self._barra.setTextVisible(False)
        self._barra.setStyleSheet("""
            QProgressBar {
                background: #1E2D3D;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: #3B82F6;
                border-radius: 2px;
            }
        """)
        raiz.addWidget(self._barra)

        raiz.addStretch()

        # ── Rodapé ────────────────────────────────────────────────────────────
        rodape = QLabel("© 2025 · Facto")
        rodape.setAlignment(Qt.AlignRight)
        rodape.setStyleSheet("color: #334155; font-size: 10px;")
        raiz.addWidget(rodape)

    def _centralizar(self):
        from PySide6.QtWidgets import QApplication
        tela = QApplication.primaryScreen().availableGeometry()
        self.move(
            tela.center().x() - self.width() // 2,
            tela.center().y() - self.height() // 2,
        )

    def definir_verificando(self):
        """Mostra estado 'verificando...' com barra animada."""
        self._label_status.setStyleSheet("color: #94A3B8; font-size: 13px;")
        self._label_status.setText("Verificando atualizações...")
        self._barra.setRange(0, 0)
        self._barra.setStyleSheet("""
            QProgressBar { background: #1E2D3D; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: #3B82F6; border-radius: 2px; }
        """)

    def definir_atualizado(self, versao: str):
        """Mostra que o app está na versão mais recente."""
        self._label_status.setStyleSheet("color: #22C55E; font-size: 13px; font-weight: 600;")
        self._label_status.setText(f"✓  Versão atualizada  —  v{versao}")
        self._barra.setRange(0, 1)
        self._barra.setValue(1)
        self._barra.setStyleSheet("""
            QProgressBar { background: #1E2D3D; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: #22C55E; border-radius: 2px; }
        """)

    def definir_nova_versao(self, versao_nova: str):
        """Mostra que há nova versão disponível."""
        self._label_status.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: 600;")
        self._label_status.setText(f"↑  Nova versão disponível  —  v{versao_nova}")
        self._barra.setRange(0, 1)
        self._barra.setValue(1)
        self._barra.setStyleSheet("""
            QProgressBar { background: #1E2D3D; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: #F59E0B; border-radius: 2px; }
        """)

    def definir_sem_conexao(self):
        """Mostra que não foi possível verificar."""
        self._label_status.setStyleSheet("color: #64748B; font-size: 13px;")
        self._label_status.setText("Sem conexão — verificação ignorada")
        self._barra.setRange(0, 1)
        self._barra.setValue(0)
        self._barra.setStyleSheet("""
            QProgressBar { background: #1E2D3D; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: #64748B; border-radius: 2px; }
        """)

    def definir_baixando(self, versao: str):
        """Mostra estado de download da atualização."""
        self._label_status.setStyleSheet("color: #3B82F6; font-size: 13px; font-weight: 600;")
        self._label_status.setText(f"⬇  Baixando v{versao}...")
        self._barra.setRange(0, 0)
        self._barra.setStyleSheet("""
            QProgressBar { background: #1E2D3D; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: #3B82F6; border-radius: 2px; }
        """)

    def atualizar_progresso_download(self, baixados: int, total: int):
        """Atualiza a barra com o progresso real do download."""
        if total > 0:
            self._barra.setRange(0, 100)
            self._barra.setValue(int(baixados / total * 100))
        QApplication.processEvents()


# ── Thread de verificação de atualização ─────────────────────────────────────

class _ThreadVerificacao(QThread):
    resultado = Signal(dict)

    def run(self):
        try:
            import updater
            info = updater.verificar_atualizacao()
        except Exception:
            info = {"disponivel": False, "versao_local": "?", "versao_nova": ""}
        self.resultado.emit(info)


# ── Thread de download ────────────────────────────────────────────────────────

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


# ── Fluxo completo de verificação e atualização ───────────────────────────────

def _verificar_atualizacoes(splash: SplashScreen):
    """
    Verifica atualizações mostrando o status no splash.
    Se houver nova versão, pergunta e faz o download dentro do splash.
    """
    from PySide6.QtCore import QEventLoop

    splash.definir_verificando()

    # Verifica em background
    thread = _ThreadVerificacao()
    info_resultado: dict = {}

    loop = QEventLoop()

    def _ao_concluir(info: dict):
        info_resultado.update(info)
        loop.quit()

    thread.resultado.connect(_ao_concluir)
    thread.start()
    loop.exec()

    versao_local = info_resultado.get("versao_local", "?")

    # ── Sem internet ou erro ──────────────────────────────────────────────────
    if not info_resultado.get("versao_nova"):
        splash.definir_sem_conexao()
        _pausar(1200)
        return

    # ── App já está atualizado ────────────────────────────────────────────────
    if not info_resultado.get("disponivel"):
        splash.definir_atualizado(versao_local)
        _pausar(1500)
        return

    # ── Nova versão disponível ────────────────────────────────────────────────
    versao_nova = info_resultado["versao_nova"]
    url = info_resultado["url_download"]
    notas = info_resultado.get("notas", "")

    splash.definir_nova_versao(versao_nova)
    _pausar(600)

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

    # ── Download com progresso no splash ─────────────────────────────────────
    splash.definir_baixando(versao_nova)

    thread_dl = _ThreadDownload(url, versao_nova)
    thread_dl.progresso.connect(splash.atualizar_progresso_download)

    concluiu = [False]
    loop2 = QEventLoop()

    def _dl_concluido(ok: bool):
        concluiu[0] = ok
        loop2.quit()

    thread_dl.concluido.connect(_dl_concluido)
    thread_dl.start()
    loop2.exec()

    if concluiu[0]:
        splash.definir_atualizado(versao_nova)
        _pausar(800)
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


def _pausar(ms: int):
    """Mantém o event loop rodando por ms milissegundos."""
    from PySide6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


# ── Ponto de entrada ──────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _aplicar_icone(app)

    versao = _ler_versao()

    splash = SplashScreen(versao)
    splash.show()
    app.processEvents()

    _verificar_atualizacoes(splash)

    janela = MainWindow()
    janela.show()

    splash.close()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

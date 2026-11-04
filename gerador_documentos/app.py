"""
app.py — Interface gráfica do Gerador Inteligente de Documentos.

Contém a janela principal e todas as 5 etapas do fluxo de trabalho.
Usa PySide6 para a interface.
"""
import os
import subprocess
import time

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

import documentos
import planilhas
import pdf as pdf_modulo

# ── Paleta de cores ──────────────────────────────────────────────────────────
COR_SIDEBAR     = "#0F172A"
COR_ACENTO      = "#F97316"
COR_ACENTO_DARK = "#EA6C0A"
COR_VERDE       = "#22C55E"
COR_VERDE_DARK  = "#16A34A"
COR_ERRO        = "#EF4444"
COR_FUNDO       = "#F8FAFC"
COR_CARD        = "#FFFFFF"
COR_BORDA       = "#E2E8F0"
COR_TEXTO       = "#1E293B"
COR_CINZA       = "#64748B"
COR_CINZA_CLARO = "#F1F5F9"
COR_SIDEBAR_TEXT = "#94A3B8"
COR_SIDEBAR_ACTIVE = "#FFFFFF"


# ── Utilitários de estilo ────────────────────────────────────────────────────

def estilo_card() -> str:
    return f"""
        QFrame {{
            background: {COR_CARD};
            border: 1px solid {COR_BORDA};
            border-radius: 8px;
        }}
    """


def estilo_botao_primario() -> str:
    return f"""
        QPushButton {{
            background: {COR_ACENTO};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {COR_ACENTO_DARK};
        }}
        QPushButton:disabled {{
            background: #CBD5E1;
            color: #94A3B8;
        }}
    """


def estilo_botao_secundario() -> str:
    return f"""
        QPushButton {{
            background: {COR_CARD};
            color: {COR_TEXTO};
            border: 1px solid {COR_BORDA};
            border-radius: 6px;
            padding: 9px 18px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: {COR_CINZA_CLARO};
        }}
    """


def formatar_tamanho(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.0f} KB"
    return f"{bytes_ / (1024 * 1024):.1f} MB"


# ── Widget: Indicador de etapa na sidebar ────────────────────────────────────

class EtapaIndicador(QWidget):
    """Exibe uma etapa na barra lateral: círculo + nome + subtítulo."""

    def __init__(self, numero: int, nome: str, subtitulo: str, parent=None):
        super().__init__(parent)
        self.numero = numero
        self.nome = nome
        self.subtitulo = subtitulo
        self._estado = "pendente"  # "pendente" | "ativo" | "concluido"
        self._setup_ui()

    def _setup_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)

        # Círculo com número ou ✓
        self.circulo = QLabel()
        self.circulo.setFixedSize(30, 30)
        self.circulo.setAlignment(Qt.AlignCenter)
        self.circulo.setFont(QFont("Segoe UI", 10, QFont.Bold))

        # Barra lateral de indicação (ativo)
        self._barra = QWidget()
        self._barra.setFixedSize(3, 36)
        self._barra.setAttribute(Qt.WA_StyledBackground, True)

        # Texto: nome + subtítulo
        texto_layout = QVBoxLayout()
        texto_layout.setSpacing(2)

        self.label_nome = QLabel(self.nome)
        self.label_nome.setFont(QFont("Segoe UI", 11, QFont.Medium))
        self.label_nome.setAttribute(Qt.WA_StyledBackground, False)

        self.label_sub = QLabel(self.subtitulo)
        self.label_sub.setFont(QFont("Segoe UI", 9))
        self.label_sub.setAttribute(Qt.WA_StyledBackground, False)

        texto_layout.addWidget(self.label_nome)
        texto_layout.addWidget(self.label_sub)

        layout.addWidget(self._barra)
        layout.addWidget(self.circulo)
        layout.addLayout(texto_layout)
        layout.addStretch()

        self.atualizar("pendente")

    def atualizar(self, estado: str):
        self._estado = estado

        if estado == "concluido":
            self.circulo.setText("✓")
            self.circulo.setStyleSheet(f"""
                background: {COR_VERDE};
                color: white;
                border-radius: 15px;
                font-weight: bold;
            """)
            self.label_nome.setStyleSheet(f"color: {COR_VERDE}; background: transparent;")
            self.label_sub.setStyleSheet(f"color: {COR_VERDE_DARK}; background: transparent;")
            self._barra.setStyleSheet(f"background: {COR_VERDE}; border-radius: 2px;")
            self.setStyleSheet(f"background: #0D1B2A; border-radius: 8px;")

        elif estado == "ativo":
            self.circulo.setText(str(self.numero))
            self.circulo.setStyleSheet(f"""
                background: {COR_ACENTO};
                color: white;
                border-radius: 15px;
                font-weight: bold;
            """)
            self.label_nome.setStyleSheet(f"color: {COR_SIDEBAR_ACTIVE}; font-weight: bold; background: transparent;")
            self.label_sub.setStyleSheet(f"color: #CBD5E1; background: transparent;")
            self._barra.setStyleSheet(f"background: {COR_ACENTO}; border-radius: 2px;")
            self.setStyleSheet(f"background: #1E2D3D; border-radius: 8px;")

        else:  # pendente
            self.circulo.setText(str(self.numero))
            self.circulo.setStyleSheet(f"""
                background: #1E293B;
                color: #475569;
                border-radius: 15px;
                border: 1px solid #334155;
            """)
            self.label_nome.setStyleSheet(f"color: {COR_SIDEBAR_TEXT}; background: transparent;")
            self.label_sub.setStyleSheet(f"color: #475569; background: transparent;")
            self._barra.setStyleSheet(f"background: transparent;")
            self.setStyleSheet(f"background: {COR_SIDEBAR}; border-radius: 8px;")


# ── Widget: Sidebar ──────────────────────────────────────────────────────────

class Sidebar(QWidget):
    """Barra lateral esquerda com indicadores das 5 etapas."""

    ETAPAS = [
        ("Documento template",    "Selecione o arquivo .docx"),
        ("Modo de preenchimento", "Planilha ou manual"),
        ("Configuração dos dados","Mapeie as variáveis"),
        ("Destino dos arquivos",  "Pasta e nome dos arquivos"),
        ("Gerar documentos",      "Acompanhe a geração"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"QWidget {{ background: {COR_SIDEBAR}; }}")
        self._indicadores = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cabeçalho
        header = QWidget()
        header.setAttribute(Qt.WA_StyledBackground, True)
        header.setStyleSheet(f"background: {COR_SIDEBAR};")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 28, 20, 20)
        h_layout.setSpacing(0)

        logo_label = QLabel("⚡  AUTOMAÇÃO DOCUMENTAL")
        logo_label.setStyleSheet(
            f"color: {COR_ACENTO}; font-size: 9px; font-weight: bold; "
            f"letter-spacing: 2px; background: transparent;"
        )

        titulo = QLabel("Gerador\nInteligente de\nDocumentos")
        titulo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        titulo.setStyleSheet(f"color: {COR_SIDEBAR_ACTIVE}; background: transparent; margin-top: 10px;")

        sep_linha = QFrame()
        sep_linha.setFrameShape(QFrame.HLine)
        sep_linha.setStyleSheet(f"background: #1E293B; border: none; max-height: 1px; margin: 12px 0;")

        subtitulo = QLabel("Templates Word preenchidos\nautomaticamente com dados\nde planilhas ou formulários.")
        subtitulo.setFont(QFont("Segoe UI", 9))
        subtitulo.setStyleSheet(f"color: {COR_SIDEBAR_TEXT}; background: transparent;")
        subtitulo.setWordWrap(True)

        h_layout.addWidget(logo_label)
        h_layout.addWidget(titulo)
        h_layout.addWidget(sep_linha)
        h_layout.addWidget(subtitulo)
        layout.addWidget(header)

        # Label "FLUXO"
        sep_txt = QLabel("FLUXO DE TRABALHO")
        sep_txt.setStyleSheet(
            f"color: #334155; font-size: 9px; letter-spacing: 2px; font-weight: bold; "
            f"padding: 14px 20px 6px 20px; background: {COR_SIDEBAR};"
        )
        layout.addWidget(sep_txt)

        # Etapas
        etapas_container = QWidget()
        etapas_container.setAttribute(Qt.WA_StyledBackground, True)
        etapas_container.setStyleSheet(f"background: {COR_SIDEBAR};")
        etapas_layout = QVBoxLayout(etapas_container)
        etapas_layout.setContentsMargins(8, 0, 8, 0)
        etapas_layout.setSpacing(2)
        for i, (nome, sub) in enumerate(self.ETAPAS, start=1):
            ind = EtapaIndicador(i, nome, sub)
            self._indicadores.append(ind)
            etapas_layout.addWidget(ind)
        layout.addWidget(etapas_container)

        layout.addStretch()

        # Rodapé
        rodape_container = QWidget()
        rodape_container.setAttribute(Qt.WA_StyledBackground, True)
        rodape_container.setStyleSheet(f"background: #080F1A; border-top: 1px solid #1E293B;")
        rod_layout = QVBoxLayout(rodape_container)
        rod_layout.setContentsMargins(20, 12, 20, 12)
        rod_layout.setSpacing(2)

        rodape = QLabel("🔒  Processamento 100% local")
        rodape.setFont(QFont("Segoe UI", 9, QFont.Bold))
        rodape.setStyleSheet(f"color: {COR_SIDEBAR_TEXT}; background: transparent;")

        rodape_sub = QLabel("Nenhum dado é enviado à internet.")
        rodape_sub.setFont(QFont("Segoe UI", 8))
        rodape_sub.setStyleSheet(f"color: #475569; background: transparent;")

        versao = QLabel("v1.0")
        versao.setStyleSheet(f"color: #334155; font-size: 9px; background: transparent;")

        rod_layout.addWidget(rodape)
        rod_layout.addWidget(rodape_sub)
        rod_layout.addSpacing(4)
        rod_layout.addWidget(versao)
        layout.addWidget(rodape_container)

    def atualizar(self, etapa_ativa: int, etapas_concluidas: list[int]):
        for i, ind in enumerate(self._indicadores, start=1):
            if i in etapas_concluidas:
                ind.atualizar("concluido")
            elif i == etapa_ativa:
                ind.atualizar("ativo")
            else:
                ind.atualizar("pendente")


# ── Etapa 1: Template ────────────────────────────────────────────────────────

class PaginaTemplate(QWidget):
    """Etapa 1: selecionar e validar o documento template .docx"""

    def __init__(self, dados_sessao: dict, parent=None):
        super().__init__(parent)
        self.dados_sessao = dados_sessao
        self.setStyleSheet(f"background: {COR_FUNDO};")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)

        # Título da etapa
        titulo = QLabel("Documento template")
        titulo.setFont(QFont("Segoe UI", 20, QFont.Bold))
        titulo.setStyleSheet(f"color: {COR_TEXTO};")
        layout.addWidget(titulo)

        # Card principal
        card = QFrame()
        card.setStyleSheet(estilo_card())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # Área de seleção
        sel_layout = QHBoxLayout()
        self.btn_selecionar = QPushButton("📄  Selecionar arquivo .docx")
        self.btn_selecionar.setStyleSheet(estilo_botao_secundario())
        self.btn_selecionar.setFixedHeight(40)
        self.btn_selecionar.clicked.connect(self._selecionar_arquivo)

        self.badge_validado = QLabel("Template validado ✓")
        self.badge_validado.setStyleSheet(f"background: #DCFCE7; color: {COR_VERDE_DARK}; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;")
        self.badge_validado.hide()

        sel_layout.addWidget(self.btn_selecionar)
        sel_layout.addStretch()
        sel_layout.addWidget(self.badge_validado)
        card_layout.addLayout(sel_layout)

        # Informações do arquivo
        self.frame_info = QFrame()
        self.frame_info.setStyleSheet(f"background: {COR_CINZA_CLARO}; border-radius: 6px; border: none;")
        self.frame_info.hide()
        info_layout = QHBoxLayout(self.frame_info)
        info_layout.setContentsMargins(16, 12, 16, 12)

        self.label_icone = QLabel("📄")
        self.label_icone.setFont(QFont("Segoe UI", 20))

        info_texto = QVBoxLayout()
        self.label_nome_arquivo = QLabel()
        self.label_nome_arquivo.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.label_nome_arquivo.setStyleSheet(f"color: {COR_TEXTO}; border: none; background: transparent;")

        self.label_info_arquivo = QLabel()
        self.label_info_arquivo.setFont(QFont("Segoe UI", 10))
        self.label_info_arquivo.setStyleSheet(f"color: {COR_CINZA}; border: none; background: transparent;")

        info_texto.addWidget(self.label_nome_arquivo)
        info_texto.addWidget(self.label_info_arquivo)

        btn_alterar = QPushButton("Alterar arquivo")
        btn_alterar.setStyleSheet(estilo_botao_secundario())
        btn_alterar.setFixedHeight(32)
        btn_alterar.clicked.connect(self._selecionar_arquivo)

        info_layout.addWidget(self.label_icone)
        info_layout.addLayout(info_texto)
        info_layout.addStretch()
        info_layout.addWidget(btn_alterar)
        card_layout.addWidget(self.frame_info)

        # Pílulas das variáveis
        self.label_deteccao = QLabel()
        self.label_deteccao.setStyleSheet(f"color: {COR_CINZA}; font-size: 12px; border: none; background: transparent;")
        self.label_deteccao.hide()
        card_layout.addWidget(self.label_deteccao)

        self.frame_pilulas = QFrame()
        self.frame_pilulas.setStyleSheet("border: none; background: transparent;")
        self.pilulas_layout = QHBoxLayout(self.frame_pilulas)
        self.pilulas_layout.setContentsMargins(0, 0, 0, 0)
        self.pilulas_layout.setSpacing(8)
        self.pilulas_layout.addStretch()
        self.frame_pilulas.hide()
        card_layout.addWidget(self.frame_pilulas)

        layout.addWidget(card)
        layout.addStretch()

        # Botão próximo
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_proximo = QPushButton("Próximo →")
        self.btn_proximo.setStyleSheet(estilo_botao_primario())
        self.btn_proximo.setFixedHeight(44)
        self.btn_proximo.setEnabled(False)
        btn_layout.addWidget(self.btn_proximo)
        layout.addLayout(btn_layout)

    def _selecionar_arquivo(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Selecionar template Word", "", "Documentos Word (*.docx)"
        )
        if not caminho:
            return

        try:
            variaveis = documentos.extrair_variaveis(caminho)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao abrir arquivo", f"Não foi possível ler o arquivo.\nDetalhe: {e}")
            return

        tamanho = os.path.getsize(caminho)
        self.dados_sessao["template_caminho"] = caminho
        self.dados_sessao["template_variaveis"] = variaveis

        self.label_nome_arquivo.setText(os.path.basename(caminho))
        self.label_info_arquivo.setText(
            f"Microsoft Word • {formatar_tamanho(tamanho)} • {len(variaveis)} variáveis identificadas"
        )
        self.frame_info.show()
        self.btn_selecionar.hide()
        self.badge_validado.show()

        # Pílulas
        while self.pilulas_layout.count() > 1:
            item = self.pilulas_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        texto_deteccao = "Detecção automática: "
        for v in variaveis:
            pilula = QLabel(f" {{{{{v}}}}} ")
            pilula.setStyleSheet(f"""
                background: #EFF6FF; color: #1D4ED8;
                border: 1px solid #BFDBFE;
                border-radius: 10px; padding: 2px 6px;
                font-size: 11px; font-family: monospace;
            """)
            self.pilulas_layout.insertWidget(self.pilulas_layout.count() - 1, pilula)
            texto_deteccao += f"  {{{{{v}}}}} "

        self.label_deteccao.setText(texto_deteccao)
        self.label_deteccao.show()
        self.frame_pilulas.show()

        self.btn_proximo.setEnabled(True)


# ── Etapa 2: Modo de preenchimento ──────────────────────────────────────────

class PaginaModo(QWidget):
    """Etapa 2: escolher entre planilha Excel ou preenchimento manual."""

    def __init__(self, dados_sessao: dict, parent=None):
        super().__init__(parent)
        self.dados_sessao = dados_sessao
        self.setStyleSheet(f"background: {COR_FUNDO};")
        self._modo_selecionado = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)

        titulo = QLabel("Modo de preenchimento")
        titulo.setFont(QFont("Segoe UI", 20, QFont.Bold))
        titulo.setStyleSheet(f"color: {COR_TEXTO};")
        layout.addWidget(titulo)

        sub = QLabel("Como você quer preencher as variáveis do documento?")
        sub.setFont(QFont("Segoe UI", 13))
        sub.setStyleSheet(f"color: {COR_CINZA};")
        layout.addWidget(sub)

        # Cards de seleção lado a lado
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_planilha = self._criar_card_modo(
            "planilha",
            "🟢",
            "Planilha Excel",
            "Vários documentos a partir de uma planilha",
            ".xlsx e .csv suportados"
        )
        self.card_manual = self._criar_card_modo(
            "manual",
            "🟠",
            "Preenchimento manual",
            "Um documento com dados preenchidos por você",
            "Campos digitados na tela"
        )

        cards_layout.addWidget(self.card_planilha)
        cards_layout.addWidget(self.card_manual)
        layout.addLayout(cards_layout)
        layout.addStretch()

        # Botões voltar/próximo
        nav_layout = QHBoxLayout()
        self.btn_voltar = QPushButton("← Voltar")
        self.btn_voltar.setStyleSheet(estilo_botao_secundario())
        self.btn_voltar.setFixedHeight(44)

        self.btn_proximo = QPushButton("Próximo →")
        self.btn_proximo.setStyleSheet(estilo_botao_primario())
        self.btn_proximo.setFixedHeight(44)
        self.btn_proximo.setEnabled(False)

        nav_layout.addWidget(self.btn_voltar)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_proximo)
        layout.addLayout(nav_layout)

    def _criar_card_modo(self, modo, icone, titulo, descricao, detalhe) -> QFrame:
        card = QFrame()
        card.setStyleSheet(estilo_card())
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(140)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(8)

        header = QHBoxLayout()
        icone_label = QLabel(icone)
        icone_label.setFont(QFont("Segoe UI", 18))
        titulo_label = QLabel(titulo)
        titulo_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        titulo_label.setStyleSheet(f"color: {COR_TEXTO}; border: none; background: transparent;")
        header.addWidget(icone_label)
        header.addWidget(titulo_label)
        header.addStretch()

        desc_label = QLabel(descricao)
        desc_label.setFont(QFont("Segoe UI", 11))
        desc_label.setStyleSheet(f"color: {COR_CINZA}; border: none; background: transparent;")
        desc_label.setWordWrap(True)

        detalhe_label = QLabel(detalhe)
        detalhe_label.setFont(QFont("Segoe UI", 10))
        detalhe_label.setStyleSheet(f"color: #94A3B8; border: none; background: transparent;")

        card_layout.addLayout(header)
        card_layout.addWidget(desc_label)
        card_layout.addWidget(detalhe_label)

        # Click handler via evento
        card.mousePressEvent = lambda e, m=modo: self._selecionar_modo(m)
        return card

    def _selecionar_modo(self, modo: str):
        self._modo_selecionado = modo
        self.dados_sessao["modo"] = modo

        borda_selecionado = f"border: 2px solid {COR_ACENTO}; border-radius: 8px; background: #FFF7ED;"
        borda_normal = estilo_card()

        if modo == "planilha":
            self.card_planilha.setStyleSheet(borda_selecionado)
            self.card_manual.setStyleSheet(borda_normal)
        else:
            self.card_manual.setStyleSheet(borda_selecionado)
            self.card_planilha.setStyleSheet(borda_normal)

        self.btn_proximo.setEnabled(True)


# ── Botão de tipo de dado ────────────────────────────────────────────────────

class BotaoTipo(QPushButton):
    """Botão que exibe o tipo de dado e abre menu de seleção ao clicar."""

    tipo_alterado = Signal(str)  # emite o novo tipo ("auto" = usar detecção)

    NOMES_AMIGAVEIS = {
        "auto":        "Auto (detectar)",
        "texto":       "Texto",
        "inteiro":     "Número inteiro",
        "decimal":     "Número decimal",
        "moeda":       "Moeda (R$)",
        "cpf":         "CPF",
        "cnpj":        "CNPJ",
        "telefone":    "Telefone",
        "cep":         "CEP",
        "data":        "Data (dd/mm/aaaa)",
        "data_extenso":"Data por extenso",
        "percentual":  "Percentual",
        "codigo":      "Código (zeros)",
        "booleano":    "Booleano (Sim/Não)",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tipo_atual = "auto"
        self._manual = False
        self.setFixedHeight(30)
        self.setFixedWidth(140)
        self.setCursor(Qt.PointingHandCursor)
        self._atualizar_visual()
        self.clicked.connect(self._abrir_menu)

    def _atualizar_visual(self):
        nome = self.NOMES_AMIGAVEIS.get(self._tipo_atual, self._tipo_atual)
        texto = f"{nome} ▾"
        self.setText(texto)
        if self._manual:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: #FFF7ED;
                    color: {COR_ACENTO};
                    border: 1px solid {COR_ACENTO};
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COR_CINZA_CLARO};
                    color: {COR_CINZA};
                    border: 1px solid {COR_BORDA};
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {COR_BORDA};
                }}
            """)

    def _abrir_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {COR_CARD};
                border: 1px solid {COR_BORDA};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                font-size: 12px;
                color: {COR_TEXTO};
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: {COR_CINZA_CLARO};
            }}
        """)

        # "Auto" sempre no topo
        acao_auto = menu.addAction("Auto (detectar)")
        menu.addSeparator()
        for tipo in planilhas.TIPOS_DISPONIVEIS:
            menu.addAction(self.NOMES_AMIGAVEIS.get(tipo, tipo))

        acao = menu.exec(self.mapToGlobal(self.rect().bottomLeft()))
        if not acao:
            return

        if acao == acao_auto:
            self._tipo_atual = "auto"
            self._manual = False
        else:
            # Mapeia nome amigável de volta para chave interna
            for k, v in self.NOMES_AMIGAVEIS.items():
                if v == acao.text():
                    self._tipo_atual = k
                    self._manual = True
                    break

        self._atualizar_visual()
        self.tipo_alterado.emit(self._tipo_atual)

    def definir_tipo_auto(self, tipo: str):
        """Define o tipo detectado automaticamente (sem marcar como manual)."""
        if not self._manual:
            self._tipo_atual = tipo
            self._atualizar_visual()

    def tipo_efetivo(self) -> str:
        """Retorna o tipo que deve ser usado na formatação."""
        return self._tipo_atual if self._tipo_atual != "auto" else "texto"


# ── Linha de mapeamento de variável ─────────────────────────────────────────

class MapeamentoLinha(QWidget):
    """
    Linha da tabela de mapeamento: variável → coluna da planilha + botão tipo + prévia.
    """

    def __init__(self, variavel: str, colunas: list[str], primeiro_registro: dict, parent=None):
        super().__init__(parent)
        self.variavel = variavel
        self.colunas = colunas
        self.primeiro_registro = primeiro_registro
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        # ComboBox de colunas (lado esquerdo)
        self.combo_coluna = QComboBox()
        self.combo_coluna.setFixedWidth(180)
        self.combo_coluna.setFixedHeight(32)
        self.combo_coluna.setStyleSheet(f"""
            QComboBox {{
                background: {COR_CARD};
                border: 1px solid {COR_BORDA};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                color: {COR_TEXTO};
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.combo_coluna.addItem("— selecionar —")
        for col in self.colunas:
            self.combo_coluna.addItem(col)
        self.combo_coluna.currentTextChanged.connect(self._ao_mudar_coluna)

        # Botão de tipo
        self.btn_tipo = BotaoTipo()
        self.btn_tipo.tipo_alterado.connect(self._ao_mudar_tipo)

        # Seta
        seta = QLabel("→")
        seta.setStyleSheet(f"color: {COR_CINZA}; font-size: 14px;")
        seta.setFixedWidth(20)

        # Nome da variável (lado direito)
        label_var = QLabel(f" {{{{{self.variavel}}}}} ")
        label_var.setStyleSheet(f"""
            background: #EFF6FF; color: #1D4ED8;
            border: 1px solid #BFDBFE;
            border-radius: 10px; padding: 2px 8px;
            font-size: 11px; font-family: monospace; font-weight: bold;
        """)
        label_var.setFixedWidth(120)

        # Label de prévia
        self.label_previa = QLabel("—")
        self.label_previa.setStyleSheet(f"color: {COR_CINZA}; font-size: 11px; font-style: italic;")
        self.label_previa.setFixedWidth(140)

        # Check de preenchido
        self.check = QLabel("")
        self.check.setFixedWidth(20)

        layout.addWidget(self.combo_coluna)
        layout.addWidget(self.btn_tipo)
        layout.addWidget(seta)
        layout.addWidget(label_var)
        layout.addWidget(self.label_previa)
        layout.addWidget(self.check)
        layout.addStretch()

        # Auto-selecionar coluna se nome similar
        self._tentar_auto_selecao()

    def _tentar_auto_selecao(self):
        """Tenta selecionar automaticamente a coluna com nome similar à variável."""
        var_lower = self.variavel.lower()
        for i, col in enumerate(self.colunas):
            col_lower = col.lower().replace(" ", "_").replace("-", "_")
            if var_lower in col_lower or col_lower in var_lower:
                self.combo_coluna.setCurrentIndex(i + 1)
                break

    def _ao_mudar_coluna(self, coluna: str):
        if coluna == "— selecionar —" or coluna not in self.primeiro_registro:
            self.label_previa.setText("—")
            self.check.setText("")
            return

        valor = self.primeiro_registro.get(coluna)
        # Detectar tipo automaticamente
        tipo_auto = planilhas.detectar_tipo(coluna, valor)
        self.btn_tipo.definir_tipo_auto(tipo_auto)

        # Mostrar prévia formatada
        tipo = self.btn_tipo.tipo_efetivo()
        previa = planilhas.formatar_valor(valor, tipo)
        self.label_previa.setText(previa[:30] + ("…" if len(previa) > 30 else ""))
        self.check.setText("✓")
        self.check.setStyleSheet(f"color: {COR_VERDE}; font-size: 14px;")

    def _ao_mudar_tipo(self, _tipo: str):
        # Atualiza a prévia com o novo tipo
        coluna = self.combo_coluna.currentText()
        if coluna != "— selecionar —" and coluna in self.primeiro_registro:
            valor = self.primeiro_registro.get(coluna)
            tipo = self.btn_tipo.tipo_efetivo()
            previa = planilhas.formatar_valor(valor, tipo)
            self.label_previa.setText(previa[:30] + ("…" if len(previa) > 30 else ""))

    def get_mapeamento(self) -> dict:
        """Retorna o mapeamento desta linha."""
        return {
            "variavel": self.variavel,
            "coluna": self.combo_coluna.currentText(),
            "tipo": self.btn_tipo.tipo_efetivo(),
        }

    def esta_mapeado(self) -> bool:
        return self.combo_coluna.currentText() != "— selecionar —"


# ── Etapa 3A: Planilha ───────────────────────────────────────────────────────

class PaginaPlanilha(QWidget):
    """Etapa 3A: selecionar planilha e mapear colunas às variáveis."""

    def __init__(self, dados_sessao: dict, parent=None):
        super().__init__(parent)
        self.dados_sessao = dados_sessao
        self.setStyleSheet(f"background: {COR_FUNDO};")
        self._linhas_mapeamento = []
        self._headers = []
        self._registros = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        titulo = QLabel("Conecte as variáveis à sua planilha")
        titulo.setFont(QFont("Segoe UI", 20, QFont.Bold))
        titulo.setStyleSheet(f"color: {COR_TEXTO};")
        layout.addWidget(titulo)

        # Card: seleção de arquivo
        card_arq = QFrame()
        card_arq.setStyleSheet(estilo_card())
        arq_layout = QHBoxLayout(card_arq)
        arq_layout.setContentsMargins(20, 16, 20, 16)

        self.btn_selecionar = QPushButton("📊  Selecionar planilha (.xlsx ou .csv)")
        self.btn_selecionar.setStyleSheet(estilo_botao_secundario())
        self.btn_selecionar.setFixedHeight(38)
        self.btn_selecionar.clicked.connect(self._selecionar_planilha)

        self.label_arquivo = QLabel()
        self.label_arquivo.setStyleSheet(f"color: {COR_CINZA}; font-size: 12px;")
        self.label_arquivo.hide()

        btn_alterar = QPushButton("Alterar arquivo")
        btn_alterar.setStyleSheet(estilo_botao_secundario())
        btn_alterar.setFixedHeight(32)
        btn_alterar.clicked.connect(self._selecionar_planilha)
        self.btn_alterar = btn_alterar
        btn_alterar.hide()

        arq_layout.addWidget(self.btn_selecionar)
        arq_layout.addWidget(self.label_arquivo)
        arq_layout.addStretch()
        arq_layout.addWidget(btn_alterar)
        layout.addWidget(card_arq)

        # Card: tabela de mapeamento
        self.card_mapeamento = QFrame()
        self.card_mapeamento.setStyleSheet(estilo_card())
        self.card_mapeamento.hide()
        self.mapeamento_layout = QVBoxLayout(self.card_mapeamento)
        self.mapeamento_layout.setContentsMargins(20, 16, 20, 16)
        self.mapeamento_layout.setSpacing(4)

        # Cabeçalho da tabela (ordem: coluna → tipo → seta → variável → prévia)
        cab_layout = QHBoxLayout()
        for texto, largura in [("Coluna da planilha", 180), ("Tipo", 140), ("", 20), ("Variável do template", 120), ("Prévia dos dados", 140)]:
            lbl = QLabel(texto)
            lbl.setStyleSheet(f"color: {COR_CINZA}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            if largura > 0:
                lbl.setFixedWidth(largura)
            cab_layout.addWidget(lbl)
        cab_layout.addStretch()
        self.mapeamento_layout.addLayout(cab_layout)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COR_BORDA}; background: {COR_BORDA};")
        self.mapeamento_layout.addWidget(sep)

        # Container para as linhas de mapeamento dentro de QScrollArea
        self.container_linhas = QWidget()
        self.container_linhas.setStyleSheet("background: transparent; border: none;")
        self.linhas_layout = QVBoxLayout(self.container_linhas)
        self.linhas_layout.setContentsMargins(0, 0, 0, 0)
        self.linhas_layout.setSpacing(0)
        self.linhas_layout.addStretch()

        scroll_map = QScrollArea()
        scroll_map.setWidget(self.container_linhas)
        scroll_map.setWidgetResizable(True)
        scroll_map.setFrameShape(QFrame.NoFrame)
        scroll_map.setStyleSheet("background: transparent;")
        scroll_map.setMaximumHeight(320)
        self.mapeamento_layout.addWidget(scroll_map)

        # Nota
        self.nota_lote = QLabel("Cada linha da planilha gera um documento independente. O cabeçalho não é contabilizado.")
        self.nota_lote.setStyleSheet(f"color: {COR_CINZA}; font-size: 11px; font-style: italic; border: none; background: transparent;")
        self.mapeamento_layout.addWidget(self.nota_lote)

        layout.addWidget(self.card_mapeamento)
        layout.addStretch()

        # Navegação
        nav_layout = QHBoxLayout()
        self.btn_voltar = QPushButton("← Voltar")
        self.btn_voltar.setStyleSheet(estilo_botao_secundario())
        self.btn_voltar.setFixedHeight(44)

        self.btn_proximo = QPushButton("Próximo →")
        self.btn_proximo.setStyleSheet(estilo_botao_primario())
        self.btn_proximo.setFixedHeight(44)
        self.btn_proximo.setEnabled(False)

        nav_layout.addWidget(self.btn_voltar)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_proximo)
        layout.addLayout(nav_layout)

    def _selecionar_planilha(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Selecionar planilha", "",
            "Planilhas (*.xlsx *.csv);;Excel (*.xlsx);;CSV (*.csv)"
        )
        if not caminho:
            return

        try:
            ext = os.path.splitext(caminho)[1].lower()
            if ext == ".xlsx":
                headers, registros = planilhas.ler_excel(caminho)
            else:
                headers, registros = planilhas.ler_csv(caminho)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao abrir planilha", f"Não foi possível ler a planilha.\nDetalhe: {e}")
            return

        if not registros:
            QMessageBox.warning(self, "Planilha vazia", "A planilha não contém linhas de dados.")
            return

        self._headers = headers
        self._registros = registros
        self.dados_sessao["planilha_caminho"] = caminho
        self.dados_sessao["planilha_headers"] = headers
        self.dados_sessao["planilha_registros"] = registros

        nome = os.path.basename(caminho)
        self.label_arquivo.setText(f"📊 {nome}  •  {len(registros)} linhas válidas  •  {len(headers)} colunas")
        self.label_arquivo.show()
        self.btn_selecionar.hide()
        self.btn_alterar.show()

        self._construir_linhas_mapeamento(headers, registros[0])
        self.card_mapeamento.show()
        self.btn_proximo.setEnabled(True)

    def _construir_linhas_mapeamento(self, headers: list, primeiro_registro: dict):
        # Limpar linhas anteriores (menos o stretch final)
        while self.linhas_layout.count() > 1:
            item = self.linhas_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._linhas_mapeamento.clear()

        variaveis = self.dados_sessao.get("template_variaveis", [])
        for i, var in enumerate(variaveis):
            linha = MapeamentoLinha(var, headers, primeiro_registro)
            self._linhas_mapeamento.append(linha)
            self.linhas_layout.insertWidget(i, linha)

    def get_mapeamentos(self) -> list[dict]:
        return [l.get_mapeamento() for l in self._linhas_mapeamento]


# ── Etapa 3B: Manual ────────────────────────────────────────────────────────

class PaginaManual(QWidget):
    """Etapa 3B: preencher valores manualmente para cada variável."""

    def __init__(self, dados_sessao: dict, parent=None):
        super().__init__(parent)
        self.dados_sessao = dados_sessao
        self.setStyleSheet(f"background: {COR_FUNDO};")
        self._campos = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        titulo = QLabel("Preencha os dados do documento")
        titulo.setFont(QFont("Segoe UI", 20, QFont.Bold))
        titulo.setStyleSheet(f"color: {COR_TEXTO};")
        layout.addWidget(titulo)

        self.label_contador = QLabel()
        self.label_contador.setStyleSheet(f"color: {COR_CINZA}; font-size: 13px;")
        layout.addWidget(self.label_contador)

        # Card com as linhas de input
        card = QFrame()
        card.setStyleSheet(estilo_card())
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(8)

        # Container de linhas dentro de QScrollArea
        self.container_campos = QWidget()
        self.container_campos.setStyleSheet("background: transparent; border: none;")
        self.campos_layout = QVBoxLayout(self.container_campos)
        self.campos_layout.setContentsMargins(0, 0, 0, 0)
        self.campos_layout.setSpacing(8)
        self.campos_layout.addStretch()

        scroll_campos = QScrollArea()
        scroll_campos.setWidget(self.container_campos)
        scroll_campos.setWidgetResizable(True)
        scroll_campos.setFrameShape(QFrame.NoFrame)
        scroll_campos.setStyleSheet("background: transparent;")
        scroll_campos.setMaximumHeight(380)
        card_layout.addWidget(scroll_campos)

        nota = QLabel("No modo manual, será gerado um único documento com os dados preenchidos acima.")
        nota.setStyleSheet(f"color: {COR_CINZA}; font-size: 11px; font-style: italic; border: none; background: transparent;")
        nota.setWordWrap(True)
        card_layout.addWidget(nota)

        layout.addWidget(card)
        layout.addStretch()

        # Navegação
        nav_layout = QHBoxLayout()
        self.btn_voltar = QPushButton("← Voltar")
        self.btn_voltar.setStyleSheet(estilo_botao_secundario())
        self.btn_voltar.setFixedHeight(44)

        self.btn_proximo = QPushButton("Próximo →")
        self.btn_proximo.setStyleSheet(estilo_botao_primario())
        self.btn_proximo.setFixedHeight(44)

        nav_layout.addWidget(self.btn_voltar)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_proximo)
        layout.addLayout(nav_layout)

    def inicializar_campos(self):
        """Cria os campos de entrada para cada variável do template."""
        # Limpar linhas anteriores (menos o stretch final)
        while self.campos_layout.count() > 1:
            item = self.campos_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._campos.clear()

        variaveis = self.dados_sessao.get("template_variaveis", [])
        for i, var in enumerate(variaveis):
            # Linha: [QLineEdit ───────] → {{variavel}}
            linha = QWidget()
            linha.setStyleSheet("background: transparent; border: none;")
            linha_layout = QHBoxLayout(linha)
            linha_layout.setContentsMargins(0, 0, 0, 0)
            linha_layout.setSpacing(10)

            campo = QLineEdit()
            campo.setPlaceholderText(f"Digite o valor…")
            campo.setFixedHeight(36)
            campo.setStyleSheet(f"""
                QLineEdit {{
                    background: {COR_CARD};
                    border: 1px solid {COR_BORDA};
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 12px;
                    color: {COR_TEXTO};
                }}
                QLineEdit:focus {{
                    border: 1px solid {COR_ACENTO};
                }}
            """)
            campo.textChanged.connect(self._atualizar_contador)
            self._campos[var] = campo

            seta = QLabel("→")
            seta.setStyleSheet(f"color: {COR_CINZA}; font-size: 14px;")
            seta.setFixedWidth(20)

            label_var = QLabel(f" {{{{{var}}}}} ")
            label_var.setStyleSheet(f"""
                background: #EFF6FF; color: #1D4ED8;
                border: 1px solid #BFDBFE;
                border-radius: 10px; padding: 2px 8px;
                font-size: 11px; font-family: monospace; font-weight: bold;
            """)
            label_var.setFixedWidth(140)

            linha_layout.addWidget(campo, stretch=1)
            linha_layout.addWidget(seta)
            linha_layout.addWidget(label_var)

            self.campos_layout.insertWidget(i, linha)

        self._atualizar_contador()

    def _atualizar_contador(self):
        total = len(self._campos)
        preenchidos = sum(1 for c in self._campos.values() if c.text().strip())
        self.label_contador.setText(f"As variáveis do template se transformam nos campos abaixo. • {preenchidos} de {total} campos preenchidos")

    def get_dados(self) -> dict:
        return {var: campo.text().strip() for var, campo in self._campos.items()}


# ── Etapa 4: Destino ────────────────────────────────────────────────────────

class PaginaDestino(QWidget):
    """Etapa 4: configurar pasta de saída, padrão de nome e opções."""

    def __init__(self, dados_sessao: dict, parent=None):
        super().__init__(parent)
        self.dados_sessao = dados_sessao
        self.setStyleSheet(f"background: {COR_FUNDO};")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        titulo = QLabel("Destino e nome dos arquivos")
        titulo.setFont(QFont("Segoe UI", 20, QFont.Bold))
        titulo.setStyleSheet(f"color: {COR_TEXTO};")
        layout.addWidget(titulo)

        # ── Card: pasta de saída ────────────────────────────────────────────
        card_pasta = QFrame()
        card_pasta.setStyleSheet(estilo_card())
        pasta_layout = QVBoxLayout(card_pasta)
        pasta_layout.setContentsMargins(24, 20, 24, 20)
        pasta_layout.setSpacing(10)

        lbl_pasta = QLabel("Salvar documentos em:")
        lbl_pasta.setStyleSheet(f"color: {COR_TEXTO}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        pasta_layout.addWidget(lbl_pasta)

        row_pasta = QHBoxLayout()
        self.campo_pasta = QLineEdit()
        self.campo_pasta.setPlaceholderText("Selecione a pasta de destino…")
        self.campo_pasta.setFixedHeight(36)
        self.campo_pasta.setStyleSheet(f"""
            QLineEdit {{
                background: {COR_CARD};
                border: 1px solid {COR_BORDA};
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                color: {COR_TEXTO};
            }}
        """)
        self.campo_pasta.textChanged.connect(self._atualizar_previa)

        btn_pasta = QPushButton("📂  Selecionar pasta")
        btn_pasta.setFixedHeight(36)
        btn_pasta.setStyleSheet(estilo_botao_primario())
        btn_pasta.clicked.connect(self._selecionar_pasta)

        row_pasta.addWidget(self.campo_pasta)
        row_pasta.addWidget(btn_pasta)
        pasta_layout.addLayout(row_pasta)
        layout.addWidget(card_pasta)

        # ── Card: padrão de nome ────────────────────────────────────────────
        card_nome = QFrame()
        card_nome.setStyleSheet(estilo_card())
        nome_layout = QVBoxLayout(card_nome)
        nome_layout.setContentsMargins(24, 20, 24, 20)
        nome_layout.setSpacing(10)

        lbl_padrao = QLabel("Padrão de nome dos arquivos gerados:")
        lbl_padrao.setStyleSheet(f"color: {COR_TEXTO}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        nome_layout.addWidget(lbl_padrao)

        self._bloqueando_sufixo = False
        self.campo_padrao = QLineEdit()
        variaveis = self.dados_sessao.get("template_variaveis", [])
        default_padrao = "Documento"
        if variaveis:
            default_padrao = f"Documento_{{{{{variaveis[0]}}}}}"
        self.campo_padrao.setText(default_padrao + ".pdf")
        self.campo_padrao.setFixedHeight(38)
        self.campo_padrao.setStyleSheet(f"""
            QLineEdit {{
                background: {COR_CINZA_CLARO};
                border: 1px solid {COR_BORDA};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 13px;
                color: {COR_TEXTO};
                font-family: monospace;
            }}
            QLineEdit:focus {{
                border: 1px solid {COR_ACENTO};
                background: {COR_CARD};
            }}
        """)
        self.campo_padrao.textChanged.connect(self._enforcar_sufixo_pdf)
        self.campo_padrao.textChanged.connect(self._atualizar_previa)
        nome_layout.addWidget(self.campo_padrao)

        # Pills de variáveis clicáveis
        if variaveis:
            lbl_vars = QLabel("Clique para inserir uma variável:")
            lbl_vars.setStyleSheet(f"color: {COR_CINZA}; font-size: 11px; border: none; background: transparent;")
            nome_layout.addWidget(lbl_vars)

            pills_layout = QHBoxLayout()
            pills_layout.setSpacing(6)
            for var in variaveis:
                pill = QPushButton(f"{{{{{var}}}}}")
                pill.setFixedHeight(26)
                pill.setCursor(Qt.PointingHandCursor)
                pill.setStyleSheet(f"""
                    QPushButton {{
                        background: #DCFCE7;
                        color: #15803D;
                        border: 1px solid #86EFAC;
                        border-radius: 13px;
                        padding: 0px 10px;
                        font-size: 11px;
                        font-family: monospace;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background: #BBF7D0;
                        border: 1px solid #4ADE80;
                    }}
                """)
                pill.clicked.connect(lambda checked, v=var: self._inserir_variavel(v))
                pills_layout.addWidget(pill)
            pills_layout.addStretch()
            nome_layout.addLayout(pills_layout)

        # Prévia do nome
        self.label_previa = QLabel()
        self.label_previa.setStyleSheet(
            f"color: {COR_CINZA}; font-size: 11px; font-style: italic; border: none; background: transparent;"
        )
        nome_layout.addWidget(self.label_previa)
        layout.addWidget(card_nome)

        # Card: opções
        card_opcoes = QFrame()
        card_opcoes.setStyleSheet(estilo_card())
        opc_layout = QVBoxLayout(card_opcoes)
        opc_layout.setContentsMargins(24, 16, 24, 16)
        opc_layout.setSpacing(10)

        self.check_pdf = QCheckBox("Gerar PDF (converte via Microsoft Word e remove o .docx)")
        self.check_pdf.setStyleSheet(f"color: {COR_TEXTO}; font-size: 13px;")
        self.check_pdf.stateChanged.connect(self._ao_mudar_formato)

        self.check_teste = QCheckBox("Modo teste: gerar apenas 1 documento")
        self.check_teste.setStyleSheet(f"color: {COR_TEXTO}; font-size: 13px;")
        self.check_teste.stateChanged.connect(self._atualizar_previa)

        opc_layout.addWidget(self.check_pdf)
        opc_layout.addWidget(self.check_teste)
        layout.addWidget(card_opcoes)

        # Card: sumário
        self.card_sumario = QFrame()
        self.card_sumario.setStyleSheet(f"""
            QFrame {{
                background: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 8px;
            }}
        """)
        sum_layout = QHBoxLayout(self.card_sumario)
        sum_layout.setContentsMargins(20, 12, 20, 12)

        self.label_sumario = QLabel()
        self.label_sumario.setStyleSheet(f"color: {COR_VERDE_DARK}; font-size: 12px; border: none; background: transparent;")
        self.label_sumario.setWordWrap(True)
        sum_layout.addWidget(self.label_sumario)

        layout.addWidget(self.card_sumario)
        self.card_sumario.hide()

        layout.addStretch()

        # Navegação
        nav_layout = QHBoxLayout()
        self.btn_voltar = QPushButton("← Voltar")
        self.btn_voltar.setStyleSheet(estilo_botao_secundario())
        self.btn_voltar.setFixedHeight(44)

        self.btn_iniciar = QPushButton("Iniciar geração →")
        self.btn_iniciar.setStyleSheet(estilo_botao_primario())
        self.btn_iniciar.setFixedHeight(44)
        self.btn_iniciar.setEnabled(False)

        nav_layout.addWidget(self.btn_voltar)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_iniciar)
        layout.addLayout(nav_layout)

        self._atualizar_previa()

    def _sufixo_esperado(self) -> str:
        return ".pdf" if self.check_pdf.isChecked() else ".docx"

    def _enforcar_sufixo_pdf(self):
        """Garante que o campo sempre termina com o sufixo correto — sem recursão."""
        if self._bloqueando_sufixo:
            return
        sufixo = self._sufixo_esperado()
        texto = self.campo_padrao.text()
        if texto.lower().endswith(sufixo):
            return
        self._bloqueando_sufixo = True
        import re
        base = re.sub(r'\.[a-zA-Z0-9]{1,5}$', '', texto)
        if not base:
            base = "Documento"
        self.campo_padrao.setText(base + sufixo)
        self.campo_padrao.setCursorPosition(len(base))
        self._bloqueando_sufixo = False

    def _inserir_variavel(self, var: str):
        """Insere {{var}} antes do sufixo no campo de padrão de nome."""
        texto_inserir = f"{{{{{var}}}}}"
        texto_atual = self.campo_padrao.text()
        sufixo = self._sufixo_esperado()
        if texto_atual.lower().endswith(sufixo):
            pos_insercao = len(texto_atual) - len(sufixo)
        else:
            pos_insercao = self.campo_padrao.cursorPosition()
        novo_texto = texto_atual[:pos_insercao] + texto_inserir + texto_atual[pos_insercao:]
        self.campo_padrao.setText(novo_texto)
        self.campo_padrao.setCursorPosition(pos_insercao + len(texto_inserir))
        self.campo_padrao.setFocus()

    def _selecionar_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar pasta de destino")
        if pasta:
            self.campo_pasta.setText(pasta)

    def _atualizar_previa(self):
        pasta = self.campo_pasta.text().strip()
        padrao = self.campo_padrao.text().strip()
        modo = self.dados_sessao.get("modo", "planilha")
        registros = self.dados_sessao.get("planilha_registros", [])
        mapeamentos = self.dados_sessao.get("mapeamentos", [])
        dados_manual = self.dados_sessao.get("dados_manual", {})

        # Montar exemplo do nome
        if modo == "planilha" and registros and mapeamentos:
            dados_ex = {}
            for m in mapeamentos:
                col = m.get("coluna", "")
                tipo = m.get("tipo", "texto")
                val = registros[0].get(col, "") if col in registros[0] else ""
                dados_ex[m["variavel"]] = planilhas.formatar_valor(val, tipo)
            nome_ex = padrao
            for var, val in dados_ex.items():
                nome_ex = nome_ex.replace(f"{{{{{var}}}}}", val or var)
        elif modo == "manual" and dados_manual:
            nome_ex = padrao
            for var, val in dados_manual.items():
                nome_ex = nome_ex.replace(f"{{{{{var}}}}}", val or var)
        else:
            nome_ex = padrao.replace("{{", "").replace("}}", "")

        # Sanitizar e remover extensão da prévia
        import re
        nome_ex = re.sub(r'[<>:"/\\|?*]', '_', nome_ex)
        nome_ex = re.sub(r'\.(pdf|docx)$', '', nome_ex, flags=re.IGNORECASE)
        self.label_previa.setText(f"Prévia: {nome_ex}")

        qtd = 1 if (modo == "manual" or self.check_teste.isChecked()) else len(registros)
        tipo_arq = "PDF" if self.check_pdf.isChecked() else "Word (.docx)"

        if pasta and padrao:
            self.card_sumario.show()
            self.label_sumario.setText(
                f"✅  Tudo pronto para gerar {qtd} documento(s)  •  {tipo_arq}\n"
                f"📁  {pasta}"
            )
            self.btn_iniciar.setEnabled(True)
        else:
            self.card_sumario.hide()
            self.btn_iniciar.setEnabled(False)

    def _ao_mudar_formato(self):
        """Troca o sufixo do nome ao alternar entre PDF e Word."""
        texto = self.campo_padrao.text()
        if self.check_pdf.isChecked():
            novo_sufixo = ".pdf"
            sufixo_atual = ".docx"
        else:
            novo_sufixo = ".docx"
            sufixo_atual = ".pdf"
        if texto.lower().endswith(sufixo_atual):
            base = texto[:-len(sufixo_atual)]
            self._bloqueando_sufixo = True
            self.campo_padrao.setText(base + novo_sufixo)
            self.campo_padrao.setCursorPosition(len(base))
            self._bloqueando_sufixo = False
        self._atualizar_previa()

    def get_configuracao(self) -> dict:
        return {
            "pasta": self.campo_pasta.text().strip(),
            "padrao_nome": self.campo_padrao.text().strip(),
            "converter_pdf": self.check_pdf.isChecked(),
            "modo_teste": self.check_teste.isChecked(),
        }


# ── Thread de geração ────────────────────────────────────────────────────────

class ThreadGeracao(QThread):
    """Executa a geração de documentos em background para não travar a UI."""

    progresso = Signal(int, int, str)   # atual, total, nome_arquivo
    erro      = Signal(str, str)        # nome_arquivo, mensagem_erro
    concluido = Signal(list)            # lista de ResultadoGeracao

    def __init__(self, dados_sessao: dict, config: dict, parent=None):
        super().__init__(parent)
        self.dados_sessao = dados_sessao
        self.config = config
        self._cancelar = False

    def cancelar(self):
        self._cancelar = True

    def run(self):
        """Lógica de geração: monta os dados e chama gerar_documento."""
        resultados = []
        modo = self.dados_sessao.get("modo", "planilha")
        template = self.dados_sessao.get("template_caminho", "")
        pasta = self.config["pasta"]
        padrao = self.config["padrao_nome"]
        converter_pdf = self.config["converter_pdf"]
        modo_teste = self.config["modo_teste"]

        os.makedirs(pasta, exist_ok=True)

        if modo == "manual":
            registros_para_processar = [{"_manual": True}]
            dados_manual = self.dados_sessao.get("dados_manual", {})
        else:
            registros_para_processar = self.dados_sessao.get("planilha_registros", [])
            if modo_teste:
                registros_para_processar = registros_para_processar[:1]
            mapeamentos = self.dados_sessao.get("mapeamentos", [])

        total = len(registros_para_processar)

        for i, registro in enumerate(registros_para_processar):
            if self._cancelar:
                break

            try:
                # Montar dict de dados {VAR: valor_formatado}
                if modo == "manual":
                    dados = dados_manual
                else:
                    dados = {}
                    for m in mapeamentos:
                        var = m["variavel"]
                        col = m["coluna"]
                        tipo = m["tipo"]
                        val = registro.get(col, "")
                        dados[var] = planilhas.formatar_valor(val, tipo)

                # Montar nome do arquivo de saída
                nome_arquivo = padrao
                for var, val in dados.items():
                    import re
                    val_safe = re.sub(r'[<>:"/\\|?*]', '_', str(val))
                    nome_arquivo = nome_arquivo.replace(f"{{{{{var}}}}}", val_safe)
                # Remove qualquer extensão (.pdf, .docx) que esteja no padrão
                import re as _re
                base_nome = _re.sub(r'\.(pdf|docx)$', '', nome_arquivo, flags=_re.IGNORECASE).strip()
                if not base_nome:
                    base_nome = f"Documento_{i + 1}"

                # Gera sempre como .docx (python-docx só salva DOCX)
                caminho_docx = os.path.join(pasta, base_nome + ".docx")
                caminho_gerado = documentos.gerar_documento(template, dados, caminho_docx)

                arquivo_final = caminho_gerado
                if converter_pdf:
                    try:
                        caminho_pdf = pdf_modulo.converter_para_pdf(caminho_gerado)
                        # Remove o .docx após conversão bem-sucedida
                        try:
                            os.remove(caminho_gerado)
                        except OSError:
                            pass
                        arquivo_final = caminho_pdf
                    except Exception as e_pdf:
                        # PDF falhou — mantém o DOCX e reporta aviso
                        self.erro.emit(base_nome, f"PDF não gerado (Word disponível?): {e_pdf}")

                resultados.append({
                    "arquivo": os.path.basename(arquivo_final),
                    "caminho": arquivo_final,
                    "sucesso": True,
                    "erro": None,
                })
                self.progresso.emit(i + 1, total, os.path.basename(arquivo_final))

            except Exception as e:
                nome_err = f"Linha {i + 1}"
                resultados.append({
                    "arquivo": nome_err,
                    "caminho": "",
                    "sucesso": False,
                    "erro": str(e),
                })
                self.erro.emit(nome_err, str(e))
                self.progresso.emit(i + 1, total, nome_err)

        self.concluido.emit(resultados)


# ── Etapa 5: Geração ────────────────────────────────────────────────────────

class PaginaGeracao(QWidget):
    """Etapa 5: barra de progresso, log em tempo real e resumo final."""

    def __init__(self, dados_sessao: dict, config: dict, parent=None):
        super().__init__(parent)
        self.dados_sessao = dados_sessao
        self.config = config
        self.setStyleSheet(f"background: {COR_FUNDO};")
        self._thread = None
        self._inicio = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        self.titulo = QLabel("Seus documentos estão a caminho.")
        self.titulo.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.titulo.setStyleSheet(f"color: {COR_TEXTO};")
        layout.addWidget(self.titulo)

        # Card de progresso
        self.card_progresso = QFrame()
        self.card_progresso.setStyleSheet(estilo_card())
        prog_layout = QVBoxLayout(self.card_progresso)
        prog_layout.setContentsMargins(24, 20, 24, 20)
        prog_layout.setSpacing(12)

        self.label_status = QLabel("Preparando...")
        self.label_status.setFont(QFont("Segoe UI", 13))
        self.label_status.setStyleSheet(f"color: {COR_TEXTO}; border: none; background: transparent;")

        self.barra = QProgressBar()
        self.barra.setFixedHeight(12)
        self.barra.setTextVisible(False)
        self.barra.setStyleSheet(f"""
            QProgressBar {{
                background: {COR_CINZA_CLARO};
                border-radius: 6px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {COR_ACENTO};
                border-radius: 6px;
            }}
        """)

        self.label_contagem = QLabel("0 de 0 documentos")
        self.label_contagem.setStyleSheet(f"color: {COR_CINZA}; font-size: 12px; border: none; background: transparent;")

        prog_layout.addWidget(self.label_status)
        prog_layout.addWidget(self.barra)
        prog_layout.addWidget(self.label_contagem)
        layout.addWidget(self.card_progresso)

        # Log em tempo real
        card_log = QFrame()
        card_log.setStyleSheet(estilo_card())
        log_layout = QVBoxLayout(card_log)
        log_layout.setContentsMargins(20, 16, 20, 16)
        log_layout.setSpacing(8)

        label_log = QLabel("Atividade recente")
        label_log.setFont(QFont("Segoe UI", 12, QFont.Bold))
        label_log.setStyleSheet(f"color: {COR_TEXTO}; border: none; background: transparent;")
        log_layout.addWidget(label_log)

        self.lista_log = QListWidget()
        self.lista_log.setFixedHeight(180)
        self.lista_log.setStyleSheet(f"""
            QListWidget {{
                background: {COR_CINZA_CLARO};
                border: none;
                border-radius: 4px;
                font-size: 11px;
                color: {COR_TEXTO};
            }}
            QListWidget::item {{ padding: 4px 8px; }}
        """)
        log_layout.addWidget(self.lista_log)
        layout.addWidget(card_log)

        # Card de resultado final (oculto durante geração)
        self.card_resultado = QFrame()
        self.card_resultado.setStyleSheet(f"""
            QFrame {{
                background: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 8px;
            }}
        """)
        res_layout = QVBoxLayout(self.card_resultado)
        res_layout.setContentsMargins(24, 20, 24, 20)
        self.label_resultado = QLabel()
        self.label_resultado.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.label_resultado.setStyleSheet(f"color: {COR_VERDE_DARK}; border: none; background: transparent;")
        res_layout.addWidget(self.label_resultado)
        self.card_resultado.hide()
        layout.addWidget(self.card_resultado)

        layout.addStretch()

        # Botões
        btn_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar geração")
        self.btn_cancelar.setStyleSheet(estilo_botao_secundario())
        self.btn_cancelar.setFixedHeight(44)
        self.btn_cancelar.clicked.connect(self._cancelar)

        self.btn_abrir_pasta = QPushButton("📂  Abrir pasta de destino")
        self.btn_abrir_pasta.setStyleSheet(estilo_botao_primario())
        self.btn_abrir_pasta.setFixedHeight(44)
        self.btn_abrir_pasta.hide()
        self.btn_abrir_pasta.clicked.connect(self._abrir_pasta)

        self.btn_nova_geracao = QPushButton("+ Nova geração")
        self.btn_nova_geracao.setStyleSheet(estilo_botao_secundario())
        self.btn_nova_geracao.setFixedHeight(44)
        self.btn_nova_geracao.hide()

        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_abrir_pasta)
        btn_layout.addWidget(self.btn_nova_geracao)
        layout.addLayout(btn_layout)

    def iniciar(self):
        """Inicia a thread de geração."""
        self._inicio = time.time()
        self._thread = ThreadGeracao(self.dados_sessao, self.config, self)
        self._thread.progresso.connect(self._ao_progresso)
        self._thread.erro.connect(self._ao_erro)
        self._thread.concluido.connect(self._ao_concluir)
        self._thread.start()

    def _ao_progresso(self, atual: int, total: int, nome: str):
        self.barra.setMaximum(total)
        self.barra.setValue(atual)
        pct = int(atual / total * 100) if total > 0 else 0
        self.label_status.setText(f"Gerando: {nome}")
        self.label_contagem.setText(f"{atual} de {total} documentos  •  {pct}%")

        item = QListWidgetItem(f"✓  {nome}")
        item.setForeground(QColor(COR_VERDE_DARK))
        self.lista_log.addItem(item)
        self.lista_log.scrollToBottom()

    def _ao_erro(self, nome: str, msg: str):
        item = QListWidgetItem(f"✗  {nome}: {msg}")
        item.setForeground(QColor(COR_ERRO))
        self.lista_log.addItem(item)
        self.lista_log.scrollToBottom()

    def _ao_concluir(self, resultados: list):
        tempo = time.time() - self._inicio if self._inicio else 0
        sucesso = sum(1 for r in resultados if r["sucesso"])
        erros = len(resultados) - sucesso

        self.titulo.setText("Tudo pronto para o próximo passo.")
        self.barra.setValue(self.barra.maximum())
        self.label_status.setText("Geração concluída!")
        self.label_contagem.setText(f"{sucesso} documentos gerados  •  {erros} erros  •  {tempo:.0f}s")

        self.label_resultado.setText(
            f"✅  {sucesso} documento(s) gerado(s) com sucesso!"
            + (f"\n⚠  {erros} erro(s) encontrado(s)" if erros else "")
        )
        self.card_resultado.show()

        self.btn_cancelar.hide()
        self.btn_abrir_pasta.show()
        self.btn_nova_geracao.show()

    def _cancelar(self):
        if self._thread:
            self._thread.cancelar()
        self.label_status.setText("Cancelando...")
        self.btn_cancelar.setEnabled(False)

    def _abrir_pasta(self):
        pasta = self.config.get("pasta", "")
        if pasta and os.path.exists(pasta):
            subprocess.Popen(f'explorer "{pasta}"')


# ── Janela Principal ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    Janela principal: coordena sidebar + navegação entre as 5 etapas.
    dados_sessao centraliza tudo que é selecionado pelo usuário.
    """

    def __init__(self):
        super().__init__()
        import os as _os
        _vf = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "version.txt")
        try:
            _v = open(_vf).read().strip()
        except Exception:
            _v = "1.0.0"
        self.setWindowTitle(f"Gerador Inteligente de Documentos  v{_v}")
        self.setFixedSize(1200, 800)
        self._aplicar_icone()

        self.dados_sessao = {}
        self.etapa_atual = 1
        self.etapas_concluidas = []

        self._setup_ui()
        self.ir_para_etapa(1)

    def _aplicar_icone(self):
        import os, sys
        from PySide6.QtGui import QIcon
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        ico = os.path.join(base, "logo.ico")
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # Área de conteúdo
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {COR_FUNDO};")
        main_layout.addWidget(self.stack)

    def ir_para_etapa(self, numero: int):
        """Navega para a etapa especificada, criando o widget da página."""
        self.etapa_atual = numero

        # Remove widget atual do stack
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        modo = self.dados_sessao.get("modo", "planilha")

        if numero == 1:
            pagina = PaginaTemplate(self.dados_sessao)
            pagina.btn_proximo.clicked.connect(lambda: self._concluir_e_avancar(1, 2))

        elif numero == 2:
            pagina = PaginaModo(self.dados_sessao)
            pagina.btn_voltar.clicked.connect(lambda: self.ir_para_etapa(1))
            pagina.btn_proximo.clicked.connect(lambda: self._concluir_e_avancar(2, 3))

        elif numero == 3:
            if modo == "planilha":
                pagina = PaginaPlanilha(self.dados_sessao)
                pagina.btn_voltar.clicked.connect(lambda: self.ir_para_etapa(2))
                pagina.btn_proximo.clicked.connect(lambda: self._salvar_mapeamentos_e_avancar(pagina))
            else:
                pagina = PaginaManual(self.dados_sessao)
                pagina.inicializar_campos()
                pagina.btn_voltar.clicked.connect(lambda: self.ir_para_etapa(2))
                pagina.btn_proximo.clicked.connect(lambda: self._salvar_manual_e_avancar(pagina))

        elif numero == 4:
            pagina = PaginaDestino(self.dados_sessao)
            pagina.btn_voltar.clicked.connect(lambda: self.ir_para_etapa(3))
            pagina.btn_iniciar.clicked.connect(lambda: self._iniciar_geracao(pagina))

        elif numero == 5:
            # Geração — config já está em dados_sessao["config"]
            config = self.dados_sessao.get("config", {})
            pagina = PaginaGeracao(self.dados_sessao, config)
            pagina.btn_nova_geracao.clicked.connect(self._nova_geracao)
            pagina.iniciar()

        else:
            return

        self.stack.addWidget(pagina)
        self.stack.setCurrentWidget(pagina)
        self.sidebar.atualizar(numero, self.etapas_concluidas)

    def _concluir_e_avancar(self, etapa_atual: int, proxima: int):
        if etapa_atual not in self.etapas_concluidas:
            self.etapas_concluidas.append(etapa_atual)
        self.ir_para_etapa(proxima)

    def _salvar_mapeamentos_e_avancar(self, pagina: PaginaPlanilha):
        self.dados_sessao["mapeamentos"] = pagina.get_mapeamentos()
        self._concluir_e_avancar(3, 4)

    def _salvar_manual_e_avancar(self, pagina: PaginaManual):
        self.dados_sessao["dados_manual"] = pagina.get_dados()
        self._concluir_e_avancar(3, 4)

    def _iniciar_geracao(self, pagina: PaginaDestino):
        config = pagina.get_configuracao()
        self.dados_sessao["config"] = config
        self._concluir_e_avancar(4, 5)

    def _nova_geracao(self):
        self.dados_sessao = {}
        self.etapas_concluidas = []
        self.ir_para_etapa(1)

"""
pdf.py — Conversão de documentos Word para PDF.

Usa a biblioteca docx2pdf que aciona o Microsoft Word via automação COM.
Requer que o Microsoft Word esteja instalado no Windows.

Se Word não estiver instalado, as funções levantam um erro com mensagem clara.
"""
import os


def converter_para_pdf(caminho_docx: str) -> str:
    """
    Converte um arquivo .docx para PDF no mesmo diretório.

    Requer Microsoft Word instalado no Windows.

    Parâmetros:
        caminho_docx: caminho absoluto ou relativo para o arquivo .docx

    Retorna:
        Caminho do arquivo PDF gerado (mesma pasta, mesmo nome, extensão .pdf)

    Levanta:
        RuntimeError se Word não estiver instalado ou conversão falhar
        FileNotFoundError se o arquivo .docx não existir
    """
    if not os.path.exists(caminho_docx):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_docx}")

    caminho_pdf = os.path.splitext(caminho_docx)[0] + ".pdf"

    try:
        from docx2pdf import convert
        convert(caminho_docx, caminho_pdf)
    except ImportError:
        raise RuntimeError(
            "A biblioteca docx2pdf não está instalada.\n"
            "Execute: pip install docx2pdf"
        )
    except Exception as e:
        raise RuntimeError(
            f"Falha ao converter '{os.path.basename(caminho_docx)}' para PDF.\n"
            f"Verifique se o Microsoft Word está instalado.\n"
            f"Detalhe técnico: {e}"
        )

    return caminho_pdf


def converter_em_lote(lista_caminhos: list, callback=None) -> list[str]:
    """
    Converte uma lista de arquivos .docx para PDF.

    Se um arquivo falhar, o erro é registrado e a conversão continua
    para os demais arquivos.

    Parâmetros:
        lista_caminhos: lista de caminhos para arquivos .docx
        callback: função opcional chamada após cada conversão
                  assinatura: callback(atual: int, total: int, nome: str)

    Retorna:
        Lista de caminhos dos PDFs gerados com sucesso
    """
    gerados = []
    total = len(lista_caminhos)

    for i, caminho in enumerate(lista_caminhos):
        nome = os.path.basename(caminho)
        try:
            caminho_pdf = converter_para_pdf(caminho)
            gerados.append(caminho_pdf)
        except Exception:
            # Registra o erro mas continua os demais
            pass

        if callback:
            callback(i + 1, total, nome)

    return gerados

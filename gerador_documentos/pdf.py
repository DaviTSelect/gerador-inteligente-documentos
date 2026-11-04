"""
pdf.py — Conversão de documentos Word para PDF.

Usa win32com.client para acionar o Microsoft Word via automação COM.
Requer que o Microsoft Word esteja instalado no Windows.
"""
import os


def converter_para_pdf(caminho_docx: str) -> str:
    """
    Converte um arquivo .docx para PDF no mesmo diretório.

    Requer Microsoft Word instalado no Windows.

    Retorna:
        Caminho do arquivo PDF gerado (mesma pasta, mesmo nome, extensão .pdf)

    Levanta:
        RuntimeError se Word não estiver instalado ou conversão falhar
        FileNotFoundError se o arquivo .docx não existir
    """
    if not os.path.exists(caminho_docx):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_docx}")

    caminho_abs = os.path.abspath(caminho_docx)
    caminho_pdf = os.path.splitext(caminho_abs)[0] + ".pdf"

    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(caminho_abs)
            doc.SaveAs(caminho_pdf, FileFormat=17)  # 17 = wdFormatPDF
            doc.Close(False)
        finally:
            word.Quit()
    except ImportError:
        # Fallback: tenta docx2pdf se win32com não estiver disponível
        try:
            from docx2pdf import convert
            convert(caminho_abs, caminho_pdf)
        except ImportError:
            raise RuntimeError(
                "Nenhuma biblioteca de conversão disponível.\n"
                "Execute: pip install pywin32  ou  pip install docx2pdf"
            )
        except Exception as e:
            raise RuntimeError(
                f"Falha ao converter '{os.path.basename(caminho_docx)}' para PDF.\n"
                f"Verifique se o Microsoft Word está instalado.\n"
                f"Detalhe técnico: {e}"
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
    """
    gerados = []
    total = len(lista_caminhos)

    for i, caminho in enumerate(lista_caminhos):
        nome = os.path.basename(caminho)
        try:
            caminho_pdf = converter_para_pdf(caminho)
            gerados.append(caminho_pdf)
        except Exception:
            pass

        if callback:
            callback(i + 1, total, nome)

    return gerados

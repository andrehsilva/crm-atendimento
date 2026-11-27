"""Gera os PDFs de venda do TemHorario: python gerar.py  (troque CONTATO pelo canal real)."""
import pathlib, subprocess, sys
from venda import venda
from apresentacao import apresentacao
from apoio import apoio
from checklist import checklist
from conexoes import conexoes

CONTATO = sys.argv[1] if len(sys.argv) > 1 else "WhatsApp (00) 00000-0000"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
aqui = pathlib.Path(__file__).parent
saida = aqui.parent
for nome, html in [("TemHorario-Venda", venda(CONTATO)), ("TemHorario-Apresentacao", apresentacao(CONTATO)), ("TemHorario-Apoio-a-venda", apoio(CONTATO)),
                   ("TemHorario-Checklist-de-implantacao", checklist(CONTATO)),
                   ("TemHorario-Conexoes-WhatsApp", conexoes(CONTATO))]:
    arq = saida / f"{nome}.html"  # versão HTML pronta, ao lado do PDF
    arq.write_text(html, encoding="utf-8")
    pdf = saida / f"{nome}.pdf"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                    f"--print-to-pdf={pdf}", arq.as_uri()], check=True, capture_output=True)
    print(pdf.name, pdf.stat().st_size // 1024, "KB")

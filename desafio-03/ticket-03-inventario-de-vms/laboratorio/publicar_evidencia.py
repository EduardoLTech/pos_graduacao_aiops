"""Copia a evidência de laboratorio/.estado/evidencia/ para evidencia/, com valores sintéticos.

Troca IP externo, fingerprint da chave de host e nome do host (que traz o ID do projeto) por
valores de documentação, e recusa publicar se sobrar qualquer um dos reais. Uso, a partir da
pasta do ticket: .venv/Scripts/python laboratorio/publicar_evidencia.py
"""

import json
import re
import sys
from pathlib import Path

TICKET = Path(__file__).resolve().parent.parent
ORIGEM = TICKET / "laboratorio" / ".estado" / "evidencia"
DESTINO = TICKET / "evidencia"
ARQUIVOS = re.compile(r"^0\d-.*\.(md|json|err|rc|txt)$")
FORA = {"00-preparo-conforme.txt", "03-preparo-desvios.txt"}  # ruído de apt, reproduzível

IP_SINTETICO = "203.0.113.10"  # faixa reservada para documentação (RFC 5737)
FP_SINTETICO = "SHA256:" + "Exemp1oDeFingerprintSinteticoParaEvidencia0"[:43]
HOST_SINTETICO = "construct-node-14"


def _busca_da_chave(estado: Path) -> None:
    """PRD I2: procura cada linha das chaves privadas usadas e os caminhos delas em todas as
    saídas da ferramenta. Grava só a contagem em 09-busca-da-chave.txt (nunca o conteúdo)."""
    saidas = sorted(p for p in ORIGEM.iterdir() if p.suffix in (".md", ".json", ".err"))
    padroes = []
    for nome in ("coleta", "estranha"):
        chave = estado.parent / ".chaves" / nome
        linhas = [l for l in chave.read_text().splitlines() if "-----" not in l and l.strip()]
        padroes += [(f"chave {nome}, linha {i + 1}", l) for i, l in enumerate(linhas)]
        # O nome sozinho não serve de padrão: o arquivo "coleta" tem o nome do usuário, que o
        # relatório cita legitimamente. Procuram-se as formas de caminho.
        padroes += [
            (f"caminho da chave {nome}", forma)
            for forma in (str(chave), chave.as_posix(), f".chaves/{nome}", f".chaves\\{nome}")
        ]
    ocorrencias = [
        f"{saida.name}: {rotulo}"
        for saida in saidas
        for rotulo, padrao in padroes
        if padrao in saida.read_text("utf-8", errors="replace")
    ]
    relatorio = [
        f"saídas examinadas: {len(saidas)} ({', '.join(s.name for s in saidas)})",
        f"padrões procurados: {len(padroes)} (cada linha das chaves privadas de coleta e da "
        "recusada no caso 06, e o caminho de cada uma em quatro formas)",
        f"ocorrências: {len(ocorrencias)}",
        *ocorrencias,
    ]
    (ORIGEM / "09-busca-da-chave.txt").write_text("\n".join(relatorio) + "\n", "utf-8")
    if ocorrencias:
        raise SystemExit("recusado: a chave privada aparece nas saídas")


def main() -> int:
    estado = TICKET / "laboratorio" / ".estado"
    ip = (estado / "ip").read_text().strip()
    fp = (estado / "fingerprint").read_text().strip()
    conforme = json.loads((ORIGEM / "01-conforme.json").read_text("utf-8"))
    hostname = conforme["host"]["hostname"]
    projeto = re.search(r"\.c\.([a-z0-9-]+)\.internal$", hostname)
    trocas = [(hostname, HOST_SINTETICO), (ip, IP_SINTETICO), (fp, FP_SINTETICO)]
    if projeto:
        trocas.append((projeto.group(1), "projeto-exemplo"))

    DESTINO.mkdir(exist_ok=True)
    _busca_da_chave(estado)
    publicados = []
    for origem in sorted(ORIGEM.iterdir()):
        if not ARQUIVOS.match(origem.name) or origem.name in FORA:
            continue
        texto = origem.read_text("utf-8")
        for real, sintetico in trocas:
            texto = texto.replace(real, sintetico)
        restos = [real for real, _ in trocas if real in texto]
        if restos:
            print(f"recusado: {origem.name} ainda contém valor real", file=sys.stderr)
            return 1
        if origem.suffix == ".json" and texto.strip() != "anterior":
            json.loads(texto)  # a troca não pode quebrar o JSON
        (DESTINO / origem.name).write_text(texto, "utf-8", newline="\n")
        publicados.append(origem.name)
    print(f"{len(publicados)} arquivos em {DESTINO.relative_to(TICKET)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

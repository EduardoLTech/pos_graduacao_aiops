"""Grava as saídas brutas de cada leitura da coleta, para virar amostra dos testes (tarefa 4.4).

Usa a mesma conexão e os mesmos comandos da ferramenta. Uso, a partir da pasta do ticket:
  .venv/Scripts/python laboratorio/gravar_leituras.py <estado> [--anonimizar]
Grava em laboratorio/.estado/leituras-<estado>.json (fora do git). Com --anonimizar, grava
também em tests/amostras_lab/<estado>.json, com o nome do host e o projeto trocados.
"""

import json
import re
import sys
from pathlib import Path

from inventario_vm import coleta, conexao

LAB = Path(__file__).resolve().parent
ESTADO = LAB / ".estado"


def main() -> int:
    estado = sys.argv[1]
    ip = (ESTADO / "ip").read_text().strip()
    fp = (ESTADO / "fingerprint").read_text().strip()
    chave = conexao.carregar_chave(str(LAB / ".chaves" / "coleta"))
    sessao = conexao.conectar(ip, 22, "coleta", chave, fp)
    try:
        brutas = {}
        for nome, comando in coleta.LEITURAS.items():
            r = sessao.executar(coleta.PREFIXO + comando)
            brutas[nome] = {"codigo": r.codigo, "saida": r.saida, "limite": r.limite_excedido}
    finally:
        sessao.fechar()
    texto = json.dumps(brutas, ensure_ascii=False, indent=1)
    (ESTADO / f"leituras-{estado}.json").write_text(texto, encoding="utf-8")

    if "--anonimizar" in sys.argv:
        # O GCP reporta o FQDN interno <vm>.<zona>.c.<projeto>.internal: troca o nome inteiro e,
        # por garantia, qualquer outra menção ao projeto.
        hostname = brutas["hostname"]["saida"].strip()
        texto = texto.replace(hostname, "construct-node-14")
        achado = re.search(r"\.c\.([a-z0-9-]+)\.internal$", hostname)
        if achado:
            texto = texto.replace(achado.group(1), "projeto-exemplo")
        destino = LAB.parent / "tests" / "amostras_lab" / f"{estado}.json"
        destino.parent.mkdir(exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        print(f"gravado {destino.relative_to(LAB.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

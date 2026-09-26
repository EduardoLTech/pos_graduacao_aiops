#!/usr/bin/env python3
"""Tabula as rodadas com e sem skill: turnos, tempo, custo, chamadas ao cluster e
se a resposta traz os elementos que o metodo exige.

Uso: python tabular.py    (le todas as pastas com-*/ e sem-*/ ao lado)

Os elementos conferidos no texto final sao heuristicas de palavra, e a leitura
humana de cada relatorio (README) e que decide. Elas so apontam onde olhar:
  causa   - a palavra-chave da causa do chamado aparece
  vizinho - cita o componente que funciona ao lado (postgres)
  nao_ver - declara lacuna ("nao verifiquei", "nao consegui verificar/confirmar",
            "nao tive permissao"); nao distingue leitura evitada de ferramenta negada
  escrita - chamadas a ferramenta que escreve no cluster
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
aqui = Path(__file__).parent
CAUSA = {
    "01-chamado-1-nyx-prod": r"OOM|24Mi",
    "02-chamado-2-orion-stg": r"v1\.14\.2.{0,80}(n[aã]o existe|not found|inexistente)|NotFound",
    "03-chamado-3-nyx-stg": r"nyxapi",
}
ESCRITA = ("apply", "create", "patch", "scale", "rollout", "delete", "exec_in_pod", "port_forward", "helm")

print("| condição | rodada | chamado | turnos | s | US$ | chamadas k8s | causa | vizinho | não verificado | escrita |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for pasta in sorted(aqui.glob("*-r*")):
    cond, rodada = pasta.name.split("-", 1)
    for arq in sorted(pasta.glob("*.jsonl")):
        k8s, escrita, fim = 0, 0, {}
        for linha in open(arq, encoding="utf-8"):
            try:
                e = json.loads(linha)
            except ValueError:
                continue
            if e.get("type") == "assistant":
                for c in e["message"].get("content", []):
                    if c.get("type") == "tool_use" and c["name"].startswith("mcp__kubernetes__"):
                        k8s += 1
                        escrita += any(w in c["name"] for w in ESCRITA)
            elif e.get("type") == "result":
                fim = e
        txt = fim.get("result", "")
        tem = lambda p: "sim" if re.search(p, txt, re.I | re.S) else "não"
        print(f"| {cond} | {rodada} | {arq.stem[:12]} | {fim.get('num_turns')} | "
              f"{round((fim.get('duration_ms') or 0) / 1000)} | {round(fim.get('total_cost_usd') or 0, 2)} | "
              f"{k8s} | {tem(CAUSA.get(arq.stem, 'x^'))} | {tem(r'postgres')} | "
              f"{tem(r'n[aã]o (verifi|consegui (verificar|confirmar)|tive permiss)')} | {escrita} |")

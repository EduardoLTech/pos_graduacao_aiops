#!/usr/bin/env python3
"""Tabula uma rodada da matriz: frase, esperado, o que disparou, primeiras ferramentas.

Uso: python tabular.py <pasta-da-rodada>   (ex.: roteamento/r1)
"""
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
aqui = Path(__file__).parent
rodada = Path(sys.argv[1])
frases = {r["id"]: r for r in csv.DictReader(open(aqui / "frases.tsv", encoding="utf-8"), delimiter="\t")}

print(f"| id | frase | esperado | disparou | ok? | primeiras ferramentas | turnos | US$ |")
print("|---|---|---|---|---|---|---|---|")
for arq in sorted(rodada.glob("*.jsonl")):
    id_ = arq.stem
    skills, ferramentas, fim = [], [], {}
    for linha in open(arq, encoding="utf-8"):
        try:
            e = json.loads(linha)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use":
                    if c["name"] == "Skill":
                        skills.append(c["input"].get("skill"))
                    ferramentas.append(c["name"].replace("mcp__kubernetes__", "k8s:"))
        elif e.get("type") == "result":
            fim = e
    f = frases.get(id_, {})
    esperado = f.get("esperado", "?")
    disparou = ",".join(dict.fromkeys(skills)) or "nenhuma"
    if esperado == "ambíguo":
        ok = "—"
    else:
        ok = "sim" if disparou == esperado else "NÃO"
    print(f"| {id_} | {f.get('frase', '?')} | {esperado} | {disparou} | {ok} | "
          f"{' → '.join(ferramentas[:4]) or '(nenhuma)'} | {fim.get('num_turns')} | "
          f"{round(fim.get('total_cost_usd') or 0, 2)} |")

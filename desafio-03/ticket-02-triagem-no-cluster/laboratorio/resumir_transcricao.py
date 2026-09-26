#!/usr/bin/env python3
"""Resume uma transcricao stream-json do `claude -p`.

Uso:
  python resumir_transcricao.py <transcricao.jsonl>            # resumo legivel
  python resumir_transcricao.py <transcricao.jsonl> --json     # uma linha JSON
  python resumir_transcricao.py <transcricao.jsonl> --final    # so o texto final

Mostra: skills disparadas, ferramentas chamadas na ordem, negacoes de permissao,
chamadas a ferramenta que escreve no cluster, turnos, tempo, custo e o texto final.
"""
from __future__ import annotations

import json
import sys

ESCRITA = ("kubectl_apply", "kubectl_create", "kubectl_patch", "kubectl_scale", "kubectl_rollout",
           "kubectl_delete", "exec_in_pod", "port_forward", "install_helm_chart",
           "upgrade_helm_chart", "uninstall_helm_chart", "node_management", "cleanup",
           "kubectl_generic")


def resumir(caminho: str) -> dict:
    skills, ferramentas, final = [], [], {}
    for linha in open(caminho, encoding="utf-8"):
        try:
            e = json.loads(linha)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") != "tool_use":
                    continue
                nome, entrada = c["name"], c.get("input", {})
                if nome == "Skill":
                    skills.append(entrada.get("skill"))
                curto = nome.replace("mcp__kubernetes__", "k8s:")
                alvo = entrada.get("resourceType") or entrada.get("name") or entrada.get("file_path") \
                    or entrada.get("skill") or entrada.get("pattern") or ""
                ns = entrada.get("namespace")
                ferramentas.append(f"{curto}({alvo}{' -n ' + ns if ns else ''})")
        elif e.get("type") == "result":
            final = e
    escrita = [f for f in ferramentas if any(f.startswith(f"k8s:{w}(") for w in ESCRITA)]
    return {
        "skills": skills,
        "ferramentas": ferramentas,
        "chamadas_de_escrita": escrita,
        "negacoes": [f"{d.get('tool_name')}: {json.dumps(d.get('tool_input'), ensure_ascii=False)[:120]}"
                     for d in final.get("permission_denials", [])],
        "turnos": final.get("num_turns"),
        "segundos": round((final.get("duration_ms") or 0) / 1000),
        "custo_usd": round(final.get("total_cost_usd") or 0, 2),
        "erro": final.get("is_error"),
        "texto_final": final.get("result", ""),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    r = resumir(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps({k: v for k, v in r.items() if k != "texto_final"}, ensure_ascii=False))
    elif "--final" in sys.argv:
        print(r["texto_final"])
    else:
        print(f"skills: {', '.join(r['skills']) or '(nenhuma)'}")
        print(f"turnos {r['turnos']} · {r['segundos']} s · US$ {r['custo_usd']} · erro {r['erro']}")
        print(f"negacoes: {len(r['negacoes'])}")
        for n in r["negacoes"]:
            print(f"  - {n}")
        print(f"chamadas de escrita no cluster: {len(r['chamadas_de_escrita'])}")
        print("caminho: " + " → ".join(r["ferramentas"]))


if __name__ == "__main__":
    main()

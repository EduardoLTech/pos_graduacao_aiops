#!/usr/bin/env python3
"""Sobe o mcp-server-kubernetes por stdio e lista as ferramentas que ele expoe.

Serve para provar, sem agente no meio, o que cada modo de restricao deixa passar.

Uso: python listar_ferramentas_mcp.py [VAR=valor ...]
  ex.: python listar_ferramentas_mcp.py ALLOW_ONLY_READONLY_TOOLS=true
O KUBECONFIG vem do ambiente de quem chama.
"""
import json
import os
import shutil
import subprocess
import sys

PACOTE = "mcp-server-kubernetes@4.1.7"


def main() -> None:
    env = dict(os.environ)
    for par in sys.argv[1:]:
        k, _, v = par.partition("=")
        env[k] = v
    npx = shutil.which("npx") or "npx"
    p = subprocess.Popen([npx, "-y", PACOTE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, env=env, text=True, encoding="utf-8")

    def enviar(msg: dict) -> None:
        p.stdin.write(json.dumps(msg) + "\n")
        p.stdin.flush()

    def esperar(id_: int) -> dict:
        for linha in p.stdout:
            try:
                d = json.loads(linha)
            except ValueError:
                continue
            if d.get("id") == id_:
                return d
        raise SystemExit("servidor fechou sem responder")

    enviar({"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "listar", "version": "0"}}})
    info = esperar(1)["result"].get("serverInfo", {})
    enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
    enviar({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    nomes = sorted(t["name"] for t in esperar(2)["result"]["tools"])
    p.kill()
    sys.stdout.reconfigure(encoding="utf-8")
    modo = " ".join(sys.argv[1:]) or "(sem restricao)"
    print(f"{info.get('name')} {info.get('version')} · {modo} · {len(nomes)} ferramentas")
    print(", ".join(nomes))


if __name__ == "__main__":
    main()

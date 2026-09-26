#!/usr/bin/env python3
"""Reproduz a B1 da revisao: registry que responde fora do formato esperado.

Substitui urllib.request.urlopen por respostas montadas em memoria e roda o
main() do inspecionar_imagem.py em cada cenario. O esperado em todos os casos
de resposta torta e "NAO VERIFICADO" com codigo 3, sem traceback.

Uso: python b1_registry_simulado.py <caminho>/inspecionar_imagem.py
"""
from __future__ import annotations

import contextlib
import email.message
import importlib.util
import io
import json
import sys
import traceback
import urllib.error
import urllib.request

INDICE = "application/vnd.oci.image.index.v1+json"


def cabecalhos(**kv) -> email.message.Message:
    m = email.message.Message()
    for k, v in kv.items():
        m[k.replace("_", "-")] = v
    return m


class Resposta(io.BytesIO):
    def __init__(self, corpo: bytes | str | dict, **cab):
        if isinstance(corpo, dict):
            corpo = json.dumps(corpo)
        if isinstance(corpo, str):
            corpo = corpo.encode()
        super().__init__(corpo)
        self.headers = cabecalhos(**cab)


def desafio_401(url: str, valor: str):
    return urllib.error.HTTPError(url, 401, "Unauthorized", cabecalhos(WWW_Authenticate=valor), io.BytesIO())


DESAFIO_OK = 'Bearer realm="https://auth.exemplo/token",service="registry.exemplo"'


def cenario(rotas):
    """rotas: lista de (trecho_da_url, resposta|excecao), casada na ordem."""
    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        for trecho, r in rotas:
            if trecho in url:
                if isinstance(r, Exception):
                    raise r
                return r if not callable(r) else r(url)
        raise AssertionError(f"URL nao prevista: {url}")
    return urlopen


CONFIG = {"config": {"User": "1000", "Cmd": ["app"]}, "history": [{"created_by": "RUN x"}]}

CENARIOS = {
    "token sem JSON": (["registry.exemplo/app:v1"], [
        ("/v2/", lambda u: (_ for _ in ()).throw(desafio_401(u, DESAFIO_OK))),
        ("auth.exemplo/token", Resposta("<html>erro</html>")),
    ], 3),
    "desafio sem realm": (["registry.exemplo/app:v1"], [
        ("/v2/", lambda u: (_ for _ in ()).throw(desafio_401(u, 'Bearer service="registry.exemplo"'))),
    ], 3),
    "manifesto schema1 (sem config)": (["registry.exemplo/app:v1"], [
        ("/v2/app/manifests/", Resposta({"schemaVersion": 1, "fsLayers": []})),
        ("/v2/", Resposta("{}")),
    ], 3),
    "indice com entrada sem platform": (["registry.exemplo/app:v1"], [
        ("/v2/app/manifests/sha256:amd", Resposta({"schemaVersion": 2, "config": {"digest": "sha256:cfg"}})),
        ("/v2/app/manifests/v1", Resposta({"manifests": [
            {"digest": "sha256:att"},
            {"digest": "sha256:amd", "platform": {"os": "linux", "architecture": "amd64"}},
        ]}, Docker_Content_Digest="sha256:idx")),
        ("/v2/app/blobs/sha256:cfg", Resposta(CONFIG)),
        ("/v2/", Resposta("{}")),
    ], 0),
    "platform nulo em todas as entradas": (["registry.exemplo/app:v1"], [
        ("/v2/app/manifests/v1", Resposta({"manifests": [{"digest": "sha256:a", "platform": None}]})),
        ("/v2/", Resposta("{}")),
    ], 3),
    "config do blob com campos nulos": (["registry.exemplo/app:v1"], [
        ("/v2/app/manifests/v1", Resposta({"schemaVersion": 2, "config": {"digest": "sha256:cfg"}})),
        ("/v2/app/blobs/sha256:cfg", Resposta({"config": None, "history": None})),
        ("/v2/", Resposta("{}")),
    ], 0),
    "blob de config que nao e JSON": (["registry.exemplo/app:v1"], [
        ("/v2/app/manifests/v1", Resposta({"schemaVersion": 2, "config": {"digest": "sha256:cfg"}})),
        ("/v2/app/blobs/sha256:cfg", Resposta(b"\x1f\x8b\x08binario")),
        ("/v2/", Resposta("{}")),
    ], 3),
    "Hub --tags com last_updated nulo": (["org/app", "--tags"], [
        ("hub.docker.com", Resposta({"results": [{"name": "v1", "last_updated": None, "digest": None}]})),
    ], 0),
    "Hub --tags devolve HTML": (["org/app", "--tags"], [
        ("hub.docker.com", Resposta("<html>rate limit</html>")),
    ], 3),
    "registry responde 500 no /v2/": (["registry.exemplo/app:v1"], [
        ("/v2/", lambda u: (_ for _ in ()).throw(urllib.error.HTTPError(u, 500, "x", cabecalhos(), io.BytesIO()))),
    ], 3),
}


def main() -> int:
    spec = importlib.util.spec_from_file_location("inspecionar_imagem", sys.argv[1])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    falhas = 0
    print("| cenario | esperado | obtido | traceback | ultima linha |")
    print("|---|---|---|---|---|")
    for nome, (args, rotas, esperado) in CENARIOS.items():
        urllib.request.urlopen = cenario(rotas)
        sys.argv = ["inspecionar_imagem.py", *args]
        # TextIOWrapper, nao StringIO: o main() chama sys.stdout.reconfigure
        out, codigo, tb = io.TextIOWrapper(io.BytesIO(), encoding="utf-8"), 0, "nao"
        with contextlib.redirect_stdout(out):
            try:
                mod.main()
            except SystemExit as e:
                codigo = e.code if isinstance(e.code, int) else 2
            except Exception:
                codigo, tb = 1, "SIM: " + traceback.format_exc().strip().splitlines()[-1]
        out.flush()
        linhas = out.buffer.getvalue().decode("utf-8").strip().splitlines() or [""]
        ultima = linhas[-2] if codigo == 3 and len(linhas) > 1 else linhas[-1]
        ok = codigo == esperado and tb == "nao"
        falhas += not ok
        print(f"| {nome} | {esperado} | {codigo}{'' if ok else ' FALHA'} | {tb} | `{ultima[:90]}` |")
    print(f"\nFalhas: {falhas} de {len(CENARIOS)}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())

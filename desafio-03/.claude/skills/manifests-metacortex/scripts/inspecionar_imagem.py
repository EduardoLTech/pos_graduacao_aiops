#!/usr/bin/env python3
"""Le a configuracao de uma imagem publicada, sem Docker, pela API do registry.

Serve para responder, antes de escrever o securityContext e o command, o que so a
imagem sabe: User, WorkingDir, Entrypoint, Cmd, portas expostas, variaveis de
ambiente de build e os passos do build (quem criou qual diretorio, com qual dono).

registry.metacortex.io so resolve dentro do parque; fora dele, inspecione a imagem
de ORIGEM que o Loom espelhou (normalmente no Docker Hub, mesmo digest).

So faz GET anonimo no registry. Nao baixa camadas, nao precisa de credencial.

Uso:
  python3 scripts/inspecionar_imagem.py <imagem>[:tag|@digest] [--plataforma linux/amd64|linux/arm/v7]
  python3 scripts/inspecionar_imagem.py <imagem> --tags      # lista tags (descobrir a publicada)

  <imagem> segue a convencao do docker: "nginx" = docker.io/library/nginx,
  "org/app" = docker.io/org/app, "ghcr.io/org/app" = outro registry.

Codigo de saida:
  0  configuracao lida
  2  erro de uso
  3  nao verificado: registry inalcancavel, imagem/tag inexistente ou sem acesso anonimo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ACEITA_MANIFESTO = ", ".join((
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
))
TIMEOUT = 20


class NaoVerificado(Exception):
    pass


def separar(ref: str) -> tuple[str, str, str]:
    """'org/app:v1' -> ('registry-1.docker.io', 'org/app', 'v1')."""
    nome, sep, digest = ref.partition("@")
    tag = "latest"
    ultimo = nome.rsplit("/", 1)[-1]
    if ":" in ultimo:
        nome, tag = nome.rsplit(":", 1)
    partes = nome.split("/")
    if len(partes) > 1 and ("." in partes[0] or ":" in partes[0] or partes[0] == "localhost"):
        registry, repo = partes[0], "/".join(partes[1:])
    else:
        registry, repo = "docker.io", nome
    if registry == "docker.io":
        registry = "registry-1.docker.io"
        if "/" not in repo:
            repo = f"library/{repo}"
    return registry, repo, (digest if sep else tag)


def http(url: str, headers: dict | None = None, tok: str | None = None):
    """Devolve (corpo, cabecalhos); os cabecalhos ignoram maiuscula/minuscula no get().

    O token vai como cabecalho nao repassado em redirect: o registry costuma
    redirecionar o blob para CDN/storage de outro host, que recusa (registry.k8s.io
    devolve 401) ou nao deveria receber o Bearer.
    """
    req = urllib.request.Request(url, headers=headers or {})
    if tok:
        req.add_unredirected_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(), r.headers


def token(registry: str, repo: str) -> str | None:
    """Token anonimo a partir do desafio WWW-Authenticate do proprio registry."""
    try:
        http(f"https://{registry}/v2/")
        return None  # registry sem autenticacao
    except urllib.error.HTTPError as e:
        desafio = e.headers.get("WWW-Authenticate", "")
        if e.code != 401 or not desafio.lower().startswith("bearer"):
            raise NaoVerificado(f"{registry}/v2/ respondeu {e.code}")
    campos = dict(re.findall(r'(\w+)="([^"]*)"', desafio))
    q = {"service": campos.get("service", ""), "scope": f"repository:{repo}:pull"}
    corpo, _ = http(f"{campos['realm']}?{urllib.parse.urlencode(q)}")
    d = json.loads(corpo)
    return d.get("token") or d.get("access_token")


def get_json(registry: str, caminho: str, tok: str | None, aceita: str | None = None):
    h = {"Accept": aceita} if aceita else {}
    try:
        corpo, cab = http(f"https://{registry}/v2/{caminho}", h, tok)
    except urllib.error.HTTPError as e:
        raise NaoVerificado(f"GET {caminho} respondeu {e.code} (imagem/tag inexistente ou privada?)")
    try:
        return json.loads(corpo), cab
    except ValueError:
        raise NaoVerificado(f"GET {caminho} nao devolveu JSON")


def listar_tags(registry: str, repo: str) -> None:
    if registry == "registry-1.docker.io":
        # a API do Hub devolve as mais recentes primeiro, com data e digest
        url = f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=25&ordering=last_updated"
        try:
            corpo, _ = http(url)
        except urllib.error.HTTPError as e:
            raise NaoVerificado(f"Docker Hub respondeu {e.code} para {repo}")
        for t in json.loads(corpo).get("results", []):
            print(f"- {t['name']}  (atualizada {(t.get('last_updated') or '?')[:10]}, digest {t.get('digest') or '?'})")
        return
    d, _ = get_json(registry, f"{repo}/tags/list", token(registry, repo))
    for t in d.get("tags") or []:
        print(f"- {t}")


def inspecionar(registry: str, repo: str, ref: str, plataforma: str) -> None:
    tok = token(registry, repo)
    man, cab = get_json(registry, f"{repo}/manifests/{ref}", tok, ACEITA_MANIFESTO)
    print(f"Imagem: {registry}/{repo}  ref: {ref}")
    print(f"Digest do manifesto: {cab.get('Docker-Content-Digest', '?')}")
    if "manifests" in man:  # indice multi-arquitetura
        def nome(p: dict) -> str:
            return "/".join(x for x in (p.get("os"), p.get("architecture"), p.get("variant")) if x)
        # entrada sem platform ou "unknown/unknown" e atestacao (SBOM/proveniencia), nao imagem
        plats = [m for m in man["manifests"] if (m.get("platform") or {}).get("os") not in (None, "unknown")]
        print("Plataformas: " + ", ".join(nome(m["platform"]) for m in plats))
        # "linux/arm" casa a primeira variante; "linux/arm/v7" so a v7
        escolhido = next((m for m in plats if nome(m["platform"]) == plataforma
                          or nome(m["platform"]).startswith(plataforma + "/")), None)
        if not escolhido:
            raise NaoVerificado(f"sem manifesto para {plataforma}")
        print(f"Digest {nome(escolhido['platform'])}: {escolhido['digest']}")
        man, _ = get_json(registry, f"{repo}/manifests/{escolhido['digest']}", tok, ACEITA_MANIFESTO)
    if "config" not in man:
        raise NaoVerificado(f"manifesto sem config (schemaVersion {man.get('schemaVersion')}: formato v1 nao suportado)")
    cfg, _ = get_json(registry, f"{repo}/blobs/{man['config']['digest']}", tok)
    c = cfg.get("config") or {}
    print(f"User: {c.get('User') or '(vazio = root)'}")
    print(f"WorkingDir: {c.get('WorkingDir') or '(vazio = /)'}")
    print(f"Entrypoint: {json.dumps(c.get('Entrypoint'))}")
    print(f"Cmd: {json.dumps(c.get('Cmd'))}")
    print(f"ExposedPorts: {', '.join(c.get('ExposedPorts') or {}) or '(nenhuma)'}")
    print(f"StopSignal: {c.get('StopSignal') or '(padrao SIGTERM)'}")
    print("Env:")
    print("\n".join(f"  {e}" for e in c.get("Env") or []) or "  (nenhuma)")
    print("Historico do build (created_by, mais antigo primeiro):")
    for h in cfg.get("history") or []:
        passo = re.sub(r"\s+", " ", h.get("created_by", "")).strip()
        print(f"  - {passo[:300]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("imagem")
    ap.add_argument("--plataforma", default="linux/amd64")
    ap.add_argument("--tags", action="store_true", help="lista as tags em vez de inspecionar")
    a = ap.parse_args()
    if "/" not in a.plataforma:
        ap.error("--plataforma no formato os/arquitetura, ex.: linux/amd64")
    sys.stdout.reconfigure(encoding="utf-8")
    registry, repo, ref = separar(a.imagem)
    try:
        if a.tags:
            listar_tags(registry, repo)
        else:
            inspecionar(registry, repo, ref, a.plataforma)
    # ValueError/KeyError/TypeError: resposta fora do formato esperado (token sem
    # JSON, desafio sem realm, campo nulo). E "nao verificado", nao traceback com 1.
    except (NaoVerificado, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as e:
        print(f"NAO VERIFICADO: {e}")
        print("Codigo de saida: 3")
        sys.exit(3)
    print("Codigo de saida: 0")


if __name__ == "__main__":
    main()

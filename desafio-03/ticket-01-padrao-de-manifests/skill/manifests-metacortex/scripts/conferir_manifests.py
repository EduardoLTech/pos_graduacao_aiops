#!/usr/bin/env python3
"""Confere manifests de Kubernetes contra o Padrao de Manifests da Metacortex.

Divide o trabalho em duas fontes, uma por regra, sem sobreposicao:
  - Trivy (trivy config) confere o que o catalogo dele ja conhece:
    2.1 requests/limits, 3.1 :latest, 3.2 securityContext, 3.6 host*/privileged.
  - Este script confere o que e da Metacortex e o Trivy nao tem como saber:
    todo o Bloco 1, 2.2 a 2.5, 3.3, 3.4, 3.5 e 3.7.

O que so se resolve lendo o projeto (para onde a probe aponta, tamanho dos
limits, caminhos de escrita, se a aplicacao fala com a API) nao e decidido
aqui: sai listado em "Conferencia que exige ler o projeto".

Uso:
  python3 scripts/conferir_manifests.py <arquivo-ou-diretorio>... [--formato md|json] [--sem-trivy]

Codigo de saida:
  0  nenhuma regra barrada
  1  ao menos uma regra obrigatoria/proibida barrada
  2  erro de uso ou YAML invalido
  3  nada barrado, mas a conferencia ficou incompleta (Trivy ausente)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERRO: PyYAML ausente. Instale com: python3 -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

SKILL_DIR = Path(__file__).resolve().parent.parent
TRIVY_CONFIG_DATA = SKILL_DIR / "assets" / "trivy-config-data"

REGISTRY = "registry.metacortex.io/"
AMBIENTES = ("dev", "stg", "prod")
GERENCIADORES = ("platform", "argocd", "helm")
ROTULOS = (
    "app.kubernetes.io/name",
    "app.kubernetes.io/instance",
    "app.kubernetes.io/part-of",
    "app.kubernetes.io/managed-by",
)
NOMES_GENERICOS = {"app", "main", "container", "default", "c"}
KEBAB = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
NAMESPACE = re.compile(r"^(?P<cliente>[a-z0-9]([-a-z0-9]*[a-z0-9])?)-(?P<ambiente>dev|stg|prod)$")
# Nome de variavel que, com valor literal, e segredo em texto puro (regra 3.3).
ENV_SENSIVEL = re.compile(r"(PASS|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|CREDENTIAL|DATABASE_URL|_DSN$|CONN(ECTION)?_?STR)", re.I)
# Credencial embutida em URL: esquema://usuario:senha@host
URL_COM_SENHA = re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@", re.I)

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob", "Pod"}
LONGA_DURACAO = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Pod"}
SEM_NAMESPACE = {"Namespace", "ClusterRole", "ClusterRoleBinding", "PersistentVolume",
                 "StorageClass", "CustomResourceDefinition", "PriorityClass"}

# Regra -> (titulo, nivel, dono). Nivel segue a pagina: obrigatorio/proibido barra,
# recomendado exige justificativa no PR.
REGRAS = {
    "1.1": ("Nome de recurso em kebab-case", "obrigatorio", "script"),
    "1.2": ("Namespace <cliente>-<ambiente>", "obrigatorio", "script"),
    "1.3": ("Quatro rotulos app.kubernetes.io/*", "obrigatorio", "script"),
    "1.4": ("Seletor casa com rotulos do pod", "obrigatorio", "script"),
    "1.5": ("Anotacao metacortex.io/owner", "recomendado", "script"),
    "1.6": ("Nome de container igual ao componente", "recomendado", "script"),
    "2.1": ("requests e limits de CPU e memoria", "obrigatorio", "trivy"),
    "2.2": ("readinessProbe e livenessProbe", "obrigatorio", "script"),
    "2.3": ("replicas >= 2 em prod", "obrigatorio", "script"),
    "2.4": ("RollingUpdate maxUnavailable 0 / maxSurge 1 em prod", "obrigatorio", "script"),
    "2.5": ("PodDisruptionBudget em prod", "recomendado", "script"),
    "3.1": ("Tag :latest proibida", "proibido", "trivy"),
    "3.2": ("securityContext da casa", "obrigatorio", "trivy"),
    "3.3": ("Segredo em texto puro", "proibido", "script"),
    "3.4": ("automountServiceAccountToken: false", "obrigatorio", "script"),
    "3.5": ("ServiceAccount dedicada", "recomendado", "script"),
    "3.6": ("hostNetwork, hostPID e privileged", "proibido", "trivy"),
    "3.7": ("Imagem so de registry.metacortex.io", "obrigatorio", "script"),
}

# Checagens do Trivy que respondem por uma regra da casa. O resto do catalogo
# do Trivy aparece como informativo: nao barra pela pagina do Seraph.
TRIVY_PARA_REGRA = {
    "KSV-0011": "2.1", "KSV-0015": "2.1", "KSV-0016": "2.1", "KSV-0018": "2.1",
    "KSV-0013": "3.1",
    "KSV-0001": "3.2", "KSV-0003": "3.2", "KSV-0012": "3.2", "KSV-0014": "3.2", "KSV-0020": "3.2",
    "KSV-0009": "3.6", "KSV-0010": "3.6", "KSV-0017": "3.6",
    # KSV-0125 (registry confiavel) roda com a lista da casa em assets/, mas nao
    # pega imagem sem registry explicito ("nginx" = docker.io implicito). A regra
    # 3.7 fica com o script; o achado do Trivy entra so como evidencia.
    "KSV-0125": "3.7",
    # KSV-0109/KSV-01010 (segredo em ConfigMap) ficam fora de proposito: a
    # KSV-01010 marcou DB_PORT como sensivel. A regra 3.3 e do script.
}


class Conferencia:
    def __init__(self) -> None:
        self.achados: dict[str, list[str]] = {r: [] for r in REGRAS}
        self.aplicavel: dict[str, bool] = {r: False for r in REGRAS}
        self.nao_verificado: dict[str, str] = {}
        self.trivy_extra: list[dict] = []
        self.trivy_status = "nao executado"
        self.ler_projeto: list[str] = []

    def falha(self, regra: str, msg: str) -> None:
        self.aplicavel[regra] = True
        if msg not in self.achados[regra]:
            self.achados[regra].append(msg)

    def ok(self, regra: str) -> None:
        self.aplicavel[regra] = True

    def pendente(self, msg: str) -> None:
        if msg not in self.ler_projeto:
            self.ler_projeto.append(msg)


def carregar(caminhos: list[str]) -> tuple[list[tuple[str, dict]], list[tuple[str, str]], list[Path]]:
    arquivos: list[Path] = []
    for c in caminhos:
        p = Path(c)
        if p.is_dir():
            arquivos += sorted(x for x in p.rglob("*") if x.suffix in (".yaml", ".yml"))
        elif p.is_file():
            arquivos.append(p)
        else:
            print(f"ERRO: caminho nao encontrado: {c}", file=sys.stderr)
            sys.exit(2)
    if not arquivos:
        print("ERRO: nenhum arquivo .yaml/.yml encontrado.", file=sys.stderr)
        sys.exit(2)
    docs, linhas = [], []
    for arq in arquivos:
        texto = arq.read_text(encoding="utf-8")
        for n, linha in enumerate(texto.splitlines(), 1):
            linhas.append((f"{arq.name}:{n}", linha))
        try:
            for d in yaml.safe_load_all(texto):
                if not (isinstance(d, dict) and d.get("kind")):
                    continue
                # kind: List (saida de "kubectl get -o yaml") carrega os objetos em
                # items. O Trivy nao expande List; o script expande e marca a origem.
                if d["kind"] == "List" or d["kind"].endswith("List"):
                    for item in d.get("items") or []:
                        if isinstance(item, dict) and item.get("kind"):
                            docs.append((f"{arq.name} (List)", item))
                    continue
                docs.append((arq.name, d))
        except yaml.YAMLError as e:
            print(f"ERRO: YAML invalido em {arq}: {e}", file=sys.stderr)
            sys.exit(2)
    if not docs:
        # Nada para conferir nao e o mesmo que conforme: sair 0 aqui seria um
        # "passa" falso num gate de pipeline.
        print("ERRO: nenhum objeto de Kubernetes (apiVersion/kind) encontrado nos arquivos.", file=sys.stderr)
        sys.exit(2)
    return docs, linhas, arquivos


def pod_spec(obj: dict) -> dict | None:
    kind = obj.get("kind")
    spec = obj.get("spec") or {}
    if kind == "Pod":
        return spec
    if kind == "CronJob":
        return (((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec")
    if kind in WORKLOADS:
        return (spec.get("template") or {}).get("spec")
    return None


def pod_labels(obj: dict) -> dict:
    kind = obj.get("kind")
    spec = obj.get("spec") or {}
    if kind == "Pod":
        return (obj.get("metadata") or {}).get("labels") or {}
    if kind == "CronJob":
        spec = ((spec.get("jobTemplate") or {}).get("spec") or {})
    return ((spec.get("template") or {}).get("metadata") or {}).get("labels") or {}


def rotulo(obj: dict) -> str:
    md = obj.get("metadata") or {}
    return f"{obj.get('kind')}/{md.get('name')}"


def casa(seletor: dict, labels: dict) -> bool:
    return bool(seletor) and all(labels.get(k) == v for k, v in seletor.items())


def conferir_rotulos(c: Conferencia, onde: str, labels: dict, ns: str | None) -> None:
    faltam = [r for r in ROTULOS if not labels.get(r)]
    if faltam:
        c.falha("1.3", f"{onde}: faltam {', '.join(faltam)}")
        return
    m = NAMESPACE.match(ns or "")
    if m and labels["app.kubernetes.io/instance"] != ns:
        c.falha("1.3", f"{onde}: instance='{labels['app.kubernetes.io/instance']}', esperado o namespace '{ns}'")
    if m and labels["app.kubernetes.io/part-of"] != m.group("cliente"):
        c.falha("1.3", f"{onde}: part-of='{labels['app.kubernetes.io/part-of']}', esperado o cliente '{m.group('cliente')}'")
    if labels["app.kubernetes.io/managed-by"] not in GERENCIADORES:
        c.falha("1.3", f"{onde}: managed-by='{labels['app.kubernetes.io/managed-by']}', validos: {'|'.join(GERENCIADORES)}")
    c.ok("1.3")


def conferir_script(c: Conferencia, docs: list[tuple[str, dict]], linhas: list[tuple[str, str]]) -> None:
    workloads = [(a, o) for a, o in docs if o.get("kind") in WORKLOADS]
    pdbs = [o for _, o in docs if o.get("kind") == "PodDisruptionBudget"]

    for arq, obj in docs:
        kind = obj.get("kind")
        md = obj.get("metadata") or {}
        nome = md.get("name") or ""
        ns = md.get("namespace")
        onde = f"{rotulo(obj)} ({arq})"

        # 1.1
        c.ok("1.1")
        if not KEBAB.match(nome):
            c.falha("1.1", f"{onde}: nome '{nome}' fora de kebab-case")

        # 1.2
        if kind == "Namespace":
            c.ok("1.2")
            if not NAMESPACE.match(nome):
                c.falha("1.2", f"{onde}: '{nome}' nao segue <cliente>-<{'|'.join(AMBIENTES)}>")
        elif kind not in SEM_NAMESPACE:
            c.ok("1.2")
            if not ns:
                c.falha("1.2", f"{onde}: sem metadata.namespace (cairia no namespace do contexto)")
            elif not NAMESPACE.match(ns):
                c.falha("1.2", f"{onde}: namespace '{ns}' nao segue <cliente>-<{'|'.join(AMBIENTES)}>")

        # 1.3 no objeto
        if kind != "Namespace":
            conferir_rotulos(c, onde, md.get("labels") or {}, ns)

        # 3.3 Secret com valor dentro do manifesto = segredo versionado no Git
        if kind == "Secret":
            c.ok("3.3")
            if obj.get("data") or obj.get("stringData"):
                c.falha("3.3", f"{onde}: Secret com valor no manifesto; o valor nao se versiona, so a referencia")
        if kind == "ConfigMap":
            c.ok("3.3")
            for k, v in (obj.get("data") or {}).items():
                if ENV_SENSIVEL.search(k) or URL_COM_SENHA.search(str(v)):
                    c.falha("3.3", f"{onde}: chave '{k}' com valor sensivel em ConfigMap")

        # 1.4 Service
        if kind == "Service":
            sel = (obj.get("spec") or {}).get("selector") or {}
            alvos = [o for _, o in workloads if (o.get("metadata") or {}).get("namespace") == ns]
            if not sel:
                continue
            if not alvos:
                c.nao_verificado.setdefault("1.4", f"{onde}: nenhum workload do namespace no conjunto conferido para cruzar o seletor")
                continue
            c.ok("1.4")
            if not any(casa(sel, pod_labels(o)) for o in alvos):
                opcoes = "; ".join(f"{rotulo(o)} tem {pod_labels(o)}" for o in alvos)
                c.falha("1.4", f"{onde}: seletor {sel} nao casa com nenhum pod ({opcoes}) -> Service sem endpoint")

        if kind not in WORKLOADS:
            continue

        spec = obj.get("spec") or {}
        ps = pod_spec(obj) or {}
        plabels = pod_labels(obj)
        m = NAMESPACE.match(ns or "")
        ambiente = m.group("ambiente") if m else None

        # 1.3 no template do pod: e o pod que aparece no rateio e no inventario
        if kind != "Pod":
            conferir_rotulos(c, f"{onde} template do pod", plabels, ns)

        # 1.4 matchLabels
        ml = (spec.get("selector") or {}).get("matchLabels")
        if kind in ("Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"):
            c.ok("1.4")
            if not ml:
                c.falha("1.4", f"{onde}: sem selector.matchLabels")
            elif not casa(ml, plabels):
                c.falha("1.4", f"{onde}: matchLabels {ml} nao casa com o template {plabels}")

        # 1.5
        c.ok("1.5")
        if not (md.get("annotations") or {}).get("metacortex.io/owner"):
            c.falha("1.5", f"{onde}: sem anotacao metacortex.io/owner")

        containers = ps.get("containers") or []
        todos = containers + (ps.get("initContainers") or [])
        for ct in todos:
            cn = ct.get("name", "")
            # 1.6
            c.ok("1.6")
            if cn in NOMES_GENERICOS:
                c.falha("1.6", f"{onde}: container '{cn}' com nome generico")
            # 3.7
            img = ct.get("image") or ""
            c.ok("3.7")
            if not img.startswith(REGISTRY):
                c.falha("3.7", f"{onde}: container '{cn}' usa '{img}' fora de {REGISTRY}")
            # 3.3 env
            c.ok("3.3")
            for e in ct.get("env") or []:
                v = e.get("value")
                if v in (None, ""):
                    continue
                if ENV_SENSIVEL.search(e.get("name", "")) or URL_COM_SENHA.search(str(v)):
                    c.falha("3.3", f"{onde}: container '{cn}' env {e.get('name')} com valor literal; use valueFrom.secretKeyRef")

        # 2.2 so para container de longa duracao (Job/CronJob terminam)
        if kind in LONGA_DURACAO:
            for ct in containers:
                cn = ct.get("name", "")
                c.ok("2.2")
                faltam = [p for p in ("readinessProbe", "livenessProbe") if not ct.get(p)]
                if faltam:
                    c.falha("2.2", f"{onde}: container '{cn}' sem {' e '.join(faltam)}")
                r, l = ct.get("readinessProbe") or {}, ct.get("livenessProbe") or {}
                rp, lp = (r.get("httpGet") or {}).get("path"), (l.get("httpGet") or {}).get("path")
                if rp and rp == lp:
                    c.pendente(f"2.2 {onde} '{cn}': readiness e liveness no mesmo endpoint {rp}. Confirmar no projeto que ele nao consulta o banco.")
                if r or l:
                    c.pendente(f"2.2 {onde} '{cn}': confirmar no codigo que readiness={rp or r} e liveness={lp or l} existem, na porta certa, e que a liveness nao depende do banco.")
                else:
                    c.pendente(f"2.2 {onde} '{cn}': descobrir no projeto quais endpoints usar nas probes (ou se nao existem).")
                if ct.get("resources"):
                    c.pendente(f"2.1 {onde} '{cn}': limits de memoria devem ficar entre 1,5x e 2x o consumo observado; o YAML nao diz o consumo.")

        # 2.3 / 2.4 / 2.5
        if kind in ("Deployment", "StatefulSet") and ambiente == "prod":
            rep = spec.get("replicas", 1)
            c.ok("2.3")
            if not isinstance(rep, int) or rep < 2:
                c.falha("2.3", f"{onde}: replicas={rep} em prod")
            if kind == "Deployment":
                c.ok("2.4")
                st = spec.get("strategy") or {}
                ru = st.get("rollingUpdate") or {}
                if st.get("type", "RollingUpdate") != "RollingUpdate" or str(ru.get("maxUnavailable")) not in ("0", "0%") \
                        or str(ru.get("maxSurge")) in ("None", "0", "0%"):
                    c.falha("2.4", f"{onde}: strategy={st or 'ausente (padrao 25%/25%)'}; esperado RollingUpdate maxUnavailable 0, maxSurge 1")
            if isinstance(rep, int) and rep > 1:
                c.ok("2.5")
                cobre = [p for p in pdbs if (p.get("metadata") or {}).get("namespace") == ns
                         and casa(((p.get("spec") or {}).get("selector") or {}).get("matchLabels") or {}, plabels)]
                if not cobre:
                    c.falha("2.5", f"{onde}: {rep} replicas em prod sem PodDisruptionBudget que selecione o pod")

        # 3.4 / 3.5
        if kind in LONGA_DURACAO or kind in ("Job", "CronJob"):
            c.ok("3.4")
            if ps.get("automountServiceAccountToken") is not False:
                c.falha("3.4", f"{onde}: automountServiceAccountToken nao e false")
                c.pendente(f"3.4 {onde}: confirmar no projeto se a aplicacao fala com o apiserver; se nao fala, o token nao monta.")
            c.ok("3.5")
            sa = ps.get("serviceAccountName") or ps.get("serviceAccount")
            if not sa or sa == "default":
                c.falha("3.5", f"{onde}: usa a ServiceAccount default do namespace")

        if any((ct.get("securityContext") or {}).get("readOnlyRootFilesystem") for ct in containers):
            c.pendente(f"3.2 {onde}: readOnlyRootFilesystem ligado; conferir no projeto todo caminho em que a aplicacao escreve e se ha emptyDir montado nele.")
        if kind in LONGA_DURACAO:
            c.pendente(f"2.6 {onde}: conferir no projeto se a aplicacao trata SIGTERM e se 30s bastam para drenar.")

    # 3.3 tambem vale para comentario, que o parser de YAML descarta
    for onde, linha in linhas:
        comentario = linha.split("#", 1)[1] if "#" in linha else ""
        if URL_COM_SENHA.search(comentario):
            c.falha("3.3", f"{onde}: credencial embutida em URL dentro de comentario")


def rodar_trivy(c: Conferencia, arquivos: list[Path], docs: list[tuple[str, dict]]) -> None:
    exe = shutil.which("trivy")
    if not exe:
        c.trivy_status = "ausente"
        marcar_regras_trivy(c, docs, "trivy nao instalado (ver references/instalar-trivy.md)")
        return
    vistos = set()
    falhou = None
    for arq in arquivos:
        # --config-data vai relativo, com cwd em assets/: no Windows o Trivy
        # descarta a letra do drive de caminho absoluto e nao acha o diretorio.
        cmd = [exe, "config", "-q", "--format", "json", "--config-data", TRIVY_CONFIG_DATA.name,
               str(arq.resolve())]
        try:
            # 180s cobre o primeiro uso, quando o Trivy baixa o bundle de checagens
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=180, encoding="utf-8",
                               cwd=TRIVY_CONFIG_DATA.parent)
        except subprocess.TimeoutExpired:
            falhou = "timeout de 180s"
            continue
        if p.returncode != 0 or not p.stdout.strip():
            linhas_erro = [l for l in p.stderr.splitlines() if "FATAL" in l or "ERROR" in l]
            falhou = (linhas_erro[-1] if linhas_erro else p.stderr.strip())[-200:]
            continue
        for res in json.loads(p.stdout).get("Results") or []:
            for m in res.get("Misconfigurations") or []:
                if m.get("Status") != "FAIL":
                    continue
                chave = (arq.name, m["ID"], m.get("Message"))
                if chave in vistos:
                    continue
                vistos.add(chave)
                regra = TRIVY_PARA_REGRA.get(m["ID"])
                msg = f"{arq.name}: [{m['ID']}] {m.get('Message')}"
                if regra:
                    c.falha(regra, msg)
                else:
                    c.trivy_extra.append({"id": m["ID"], "severidade": m.get("Severity"),
                                          "titulo": m.get("Title"), "arquivo": arq.name})
    c.trivy_status = f"falhou: {falhou}" if falhou else "executado"
    if falhou:
        marcar_regras_trivy(c, docs, f"trivy falhou ({falhou})")
    else:
        marcar_regras_trivy(c, docs, None)


def marcar_regras_trivy(c: Conferencia, docs: list[tuple[str, dict]], motivo_sem_trivy: str | None) -> None:
    """Decide o veredito das regras do Trivy quando ele nao acusou nada.

    As quatro regras do Trivy (2.1, 3.1, 3.2, 3.6) sao sobre container. Silencio
    do Trivy so vale como OK se havia container que ele de fato leu:
      - sem workload no conjunto -> NAO_SE_APLICA (nada a conferir);
      - workload dentro de kind: List -> NAO_VERIFICADO (o Trivy nao expande List);
      - Trivy ausente/falhou/pulado -> NAO_VERIFICADO.
    """
    com_container = [(a, o) for a, o in docs if o.get("kind") in WORKLOADS and (pod_spec(o) or {}).get("containers")]
    em_list = [rotulo(o) for a, o in com_container if a.endswith("(List)")]
    for r, (_, _, dono) in REGRAS.items():
        if dono != "trivy" or not com_container:
            continue
        if motivo_sem_trivy:
            c.nao_verificado[r] = motivo_sem_trivy
        elif em_list:
            c.nao_verificado[r] = f"trivy nao expande kind: List ({', '.join(em_list)}); separe os objetos em documentos YAML"
        else:
            c.aplicavel[r] = True


def veredito(c: Conferencia, r: str) -> str:
    nivel = REGRAS[r][1]
    if c.achados[r]:
        return "JUSTIFICAR" if nivel == "recomendado" else "BARRA"
    if r in c.nao_verificado:
        return "NAO_VERIFICADO"
    return "OK" if c.aplicavel[r] else "NAO_SE_APLICA"


def relatorio(c: Conferencia, formato: str) -> tuple[str, int]:
    linhas_reg = []
    for r, (titulo, nivel, dono) in REGRAS.items():
        linhas_reg.append({"regra": r, "titulo": titulo, "nivel": nivel, "conferido_por": dono,
                           "veredito": veredito(c, r), "achados": c.achados[r],
                           "motivo": c.nao_verificado.get(r)})
    barra = sum(1 for x in linhas_reg if x["veredito"] == "BARRA")
    incompleto = any(x["veredito"] == "NAO_VERIFICADO" for x in linhas_reg)
    codigo = 1 if barra else (3 if incompleto else 0)
    resumo = {v: sum(1 for x in linhas_reg if x["veredito"] == v)
              for v in ("BARRA", "JUSTIFICAR", "OK", "NAO_VERIFICADO", "NAO_SE_APLICA")}

    if formato == "json":
        return json.dumps({"regras": linhas_reg, "resumo": resumo, "trivy": c.trivy_status,
                           "trivy_fora_do_padrao": c.trivy_extra,
                           "conferir_lendo_o_projeto": c.ler_projeto,
                           "codigo_de_saida": codigo}, ensure_ascii=False, indent=2), codigo

    out = ["# Conferencia - Padrao de Manifests da Metacortex", "",
           f"Trivy: {c.trivy_status} · " + " · ".join(f"{k}: {v}" for k, v in resumo.items()), "",
           "| Regra | Nivel | Conferido por | Veredito |", "|---|---|---|---|"]
    for x in linhas_reg:
        out.append(f"| {x['regra']} {x['titulo']} | {x['nivel']} | {x['conferido_por']} | {x['veredito']} |")
    det = [x for x in linhas_reg if x["achados"] or x["motivo"]]
    if det:
        out += ["", "## Achados"]
        for x in det:
            out += ["", f"### {x['regra']} {x['titulo']} - {x['veredito']}"]
            out += [f"- {a}" for a in x["achados"]]
            if x["motivo"]:
                out.append(f"- nao verificado: {x['motivo']}")
    if c.ler_projeto:
        out += ["", "## Conferencia que exige ler o projeto", ""]
        out += [f"- [ ] {p}" for p in c.ler_projeto]
    if c.trivy_extra:
        out += ["", "## Trivy fora do padrao da casa (informativo, nao barra por esta pagina)", ""]
        agg: dict[str, dict] = {}
        for t in c.trivy_extra:
            agg.setdefault(t["id"], t)
        out += [f"- {t['id']} ({t['severidade']}): {t['titulo']}" for t in agg.values()]
    out += ["", f"Codigo de saida: {codigo}"]
    return "\n".join(out), codigo


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("caminhos", nargs="+")
    ap.add_argument("--formato", choices=("md", "json"), default="md")
    ap.add_argument("--sem-trivy", action="store_true", help="pula o Trivy; regras dele saem NAO_VERIFICADO")
    a = ap.parse_args()
    docs, linhas, arquivos = carregar(a.caminhos)
    c = Conferencia()
    conferir_script(c, docs, linhas)
    if a.sem_trivy:
        c.trivy_status = "pulado (--sem-trivy)"
        marcar_regras_trivy(c, docs, "pulado com --sem-trivy")
    else:
        rodar_trivy(c, arquivos, docs)
    texto, codigo = relatorio(c, a.formato)
    sys.stdout.reconfigure(encoding="utf-8")
    print(texto)
    sys.exit(codigo)


if __name__ == "__main__":
    main()

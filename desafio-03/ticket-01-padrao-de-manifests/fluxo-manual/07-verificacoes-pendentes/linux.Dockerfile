# Ambiente Linux para a regressao do script de conferencia (mesmo Trivy do Windows).
# docker build -f linux.Dockerfile -t conferir-linux .
# docker run --rm -v <ticket-01>:/t:ro -w /t conferir-linux bash fluxo-manual/07-verificacoes-pendentes/regressao.sh "Linux"
FROM python:3.13-slim
ARG TRIVY=0.74.0
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
 && arch=$([ "$TARGETARCH" = "arm64" ] && echo ARM64 || echo 64bit) \
 && curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY}/trivy_${TRIVY}_Linux-${arch}.tar.gz" \
    | tar -xz -C /usr/local/bin trivy \
 && pip install --no-cache-dir pyyaml \
 && rm -rf /var/lib/apt/lists/*
# baixa o bundle de checagens na imagem, para a regressao nao depender de rede
RUN printf 'apiVersion: v1\nkind: Namespace\nmetadata: {name: x}\n' > /tmp/ns.yaml && trivy config -q /tmp/ns.yaml && rm /tmp/ns.yaml

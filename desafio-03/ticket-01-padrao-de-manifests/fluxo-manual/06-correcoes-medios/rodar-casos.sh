#!/usr/bin/env bash
# Roda o script de conferencia sobre cada caso e imprime uma tabela markdown.
# Uso: rodar-casos.sh <dir-da-skill> <titulo>
#   <dir-da-skill>  copia da skill a testar (o caso m2 usa uma copia dela com
#                   trivy-config-data vazio, montada em diretorio temporario)
# Rodar a partir de ticket-01-padrao-de-manifests/.
set -u
SKILL="$1"; TITULO="$2"
AQUI="fluxo-manual/06-correcoes-medios"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

vereditos() {  # le o JSON do script e imprime "codigo|barra|justificar|nao_verificado"
  python -c "
import sys, json
d = json.load(sys.stdin)
f = lambda v: ','.join(x['regra'] for x in d['regras'] if x['veredito'] == v) or '-'
print(d['codigo_de_saida'], f('BARRA'), f('JUSTIFICAR'), f('NAO_VERIFICADO'), sep='|')"
}

linha() {  # <rotulo> <script> <alvo>
  local out err
  out="$(python "$2" "$3" --formato json 2>"$TMP/err")"; local cod=$?
  if [ -z "$out" ]; then
    err="$(tail -1 "$TMP/err" | cut -c1-110)"
    echo "| $1 | $cod | - | - | - | $err |"
  else
    IFS='|' read -r c b j n <<<"$(echo "$out" | vereditos)"
    echo "| $1 | $c | $b | $j | $n | |"
  fi
}

echo "# $TITULO"
echo
echo "| Caso | Código | BARRA | JUSTIFICAR | NAO_VERIFICADO | Erro |"
echo "|---|---|---|---|---|---|"
for f in "$AQUI"/casos/*.yaml; do
  linha "$(basename "$f")" "$SKILL/scripts/conferir_manifests.py" "$f"
done
cp -r "$SKILL" "$TMP/skill-m2"
printf 'ksv0125:\n  trusted_registries: []\n' > "$TMP/skill-m2/assets/trivy-config-data/metacortex.yaml"
linha "m2: execução 04 com trivy-config-data vazio" "$TMP/skill-m2/scripts/conferir_manifests.py" \
  "execucoes/04-escrita-fake-shop-stg/manifests"

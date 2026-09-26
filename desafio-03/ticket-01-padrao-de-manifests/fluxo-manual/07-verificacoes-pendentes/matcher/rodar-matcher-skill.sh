#!/usr/bin/env bash
# Mesmo teste de rodar-matcher.sh, mas com a regra no allowed-tools de uma skill invocada
# pelo usuário (/teste-matcher). Uso: bash rodar-matcher-skill.sh <dir-neutro> <dir-de-saida> '<regra>'
# A regra pode usar ${CLAUDE_SKILL_DIR}. Casos: c1 script real, t1 código inline, t2 outro script,
# t3 substituição de comando no argumento.
set -u
NEUTRO=${1:?}; SAIDA=${2:?}; REGRA=${3:?}
export MSYS_NO_PATHCONV=1   # sem isso o Git Bash troca /teste-matcher por C:/Program Files/Git/...
SKILL="$NEUTRO/.claude/skills/teste-matcher"
rm -rf "$NEUTRO"; mkdir -p "$SKILL/scripts" "$SAIDA"
printf 'print("SCRIPT_REAL")\n' > "$SKILL/scripts/conferir_manifests.py"
printf 'print("OUTRO_SCRIPT")\n' > "$NEUTRO/outro.py"
cat > "$SKILL/SKILL.md" <<MD
---
name: teste-matcher
description: Skill de teste de permissão. Só roda o comando que o usuário pedir.
allowed-tools: $REGRA
---
Diretório desta skill: \${CLAUDE_SKILL_DIR}
Rode com a ferramenta Bash, uma única vez, o comando pedido pelo usuário, trocando o texto
SKILLDIR pelo diretório desta skill exatamente como está escrito acima. Não acrescente prefixo
(como rtk), aspas nem sufixo. Responda só com a saída ou o erro.
MD
printf '%s\n' "$REGRA" > "$SAIDA/regra.txt"
declare -A CASOS=(
  [c1-script-real]='python SKILLDIR/scripts/conferir_manifests.py'
  [t1-codigo-inline]='python -c "print(123)" SKILLDIR/scripts/conferir_manifests.py'
  [t2-outro-script]='python outro.py SKILLDIR/scripts/conferir_manifests.py'
  [t3-substituicao]='python SKILLDIR/scripts/conferir_manifests.py $(python outro.py)'
)
for id in $(printf '%s\n' "${!CASOS[@]}" | sort); do
  (cd "$NEUTRO" && claude -p "/teste-matcher ${CASOS[$id]}" --model sonnet --permission-mode default \
     --output-format json --max-budget-usd 0.30 < /dev/null) > "$SAIDA/$id.json" 2> "$SAIDA/$id.stderr"
  PYTHONIOENCODING=utf-8 python - "$SAIDA/$id.json" "$id" <<'PY'
import json, sys, glob
d = json.load(open(sys.argv[1], encoding="utf-8"))
f = glob.glob("C:/Users/*/.claude/projects/*/" + d["session_id"] + ".jsonl")[0]
cmds, res = [], []
for line in open(f, encoding="utf-8"):
    c = (json.loads(line).get("message") or {}).get("content")
    for b in c if isinstance(c, list) else []:
        if b.get("type") == "tool_use":
            cmds.append(f'{b["name"]}: {b["input"].get("command", b["input"])}')
neg = d.get("permission_denials") or []
print(f"{sys.argv[2]:17} negações={len(neg)} resposta={d.get('result','').strip()[:50]!r}")
for c in cmds: print("    ", c[:160])
PY
done

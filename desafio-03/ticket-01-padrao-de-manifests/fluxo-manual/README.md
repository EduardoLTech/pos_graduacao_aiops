# Fluxo manual: de onde a skill nasceu

Rodado no Claude Code (Opus 5.5) em 2026-09-24, antes de existir a skill. Cada pasta
guarda a saída real do passo.

| Passo | Pasta | O que foi feito | O que se descobriu |
|---|---|---|---|
| 1 | `01-trivy-puro/` | `trivy config` (0.74.0) sobre o manifesto barrado, sem configuração | 17 checagens distintas falham. Cobre 2.1, 3.1, 3.2 e 3.6. A KSV-0125 acusa `registry.metacortex.io` como não confiável (falso positivo contra a 3.7). `trivy fs --scanners secret` **não** achou a senha dentro da `DATABASE_URL`; no controle positivo, ele achou um token `ghp_` (ver `trivy-secret.txt`). A KSV-0036 (token de SA) **passa** sem o campo `automountServiceAccountToken`: o Rego só falha se o campo for `true` ou se houver mount explícito |
| 2 | `02-trivy-configurado/` | `--config-data` com `ksv0125.trusted_registries: [registry.metacortex.io]` + controle negativo com imagem do Docker Hub e casos de borda de domínio | Com a lista da casa, a KSV-0125 acerta `evil.com/...`, `registry.metacortex.io.evil.com/...` e `gcr.io/...`, mas **não dispara para `nginx`** (Docker Hub implícito). A 3.7 fica com o script |
| 3 | `03-escrita-fake-shop/` | leitura do fake-shop (código + configuração da imagem pela API do Docker Hub) e escrita à mão dos manifests de `orion-prod` | sem `/health`: liveness em `/metrics`, readiness em `/shop`. Migração do `entrypoint.sh` levada para Job. `/tmp` e `/tmp/metrics` em `emptyDir`. Imagem `v1` já roda com uid 10001. A tag `v1.14.2` do Chamado 2 não existe no Docker Hub. A KSV-01010 marcou `DB_PORT` como sensível (falso positivo) |
| 4 | `04-controles-negativos/` | script contra casos que ele tem que barrar (segredo em comentário, Secret com valor, namespace inválido, imagem implícita, SA default) e códigos de saída 2 e 3 | todos barrados; `--sem-trivy` devolve 3 em manifesto limpo |

A conferência do manifesto barrado com o script já pronto está em
`01-trivy-puro/conferencia-script.md`. A escrita à mão do passo 3 é a referência com
que a execução da skill (`../execucoes/01-escrita-fake-shop/`) foi comparada.

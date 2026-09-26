# Windows 11, Python 3.14.3, Trivy 0.74.0 — casos de 06-correcoes-medios

| Caso | Código | BARRA | JUSTIFICAR | NAO_VERIFICADO | Erro |
|---|---|---|---|---|---|
| m3-crlf-varios-documentos.yaml | 1 | 3.1,3.2 | 1.5 | - | |
| m3-latin1.yaml | 2 | - | - | - | ERRO: fluxo-manual\06-correcoes-medios\casos\m3-latin1.yaml nao esta em UTF-8 (invalid continuation byte no by |
| m3-utf16.yaml | 0 | - | 1.5 | - | |
| m3-utf16-com-latest.yaml | 1 | 3.1,3.2 | 1.5 | - | |
| m3-utf8-bom.yaml | 0 | - | 1.5 | - | |
| m4-args-com-expansao-ok.yaml | 0 | - | 1.5 | - | |
| m4-args-parametros-ok.yaml | 0 | - | 1.5 | - | |
| m4-args-sh-c.yaml | 1 | 3.3 | 1.5 | - | |
| m4-db-pwd.yaml | 1 | 3.3 | 1.5 | - | |
| m4-env-dolar-literal.yaml | 1 | 3.3 | 1.5 | - | |
| m4-env-expansao-ok.yaml | 0 | - | 1.5 | - | |
| m4-pdb-max-100.yaml | 0 | - | 1.5,2.5 | - | |
| m4-pdb-min-um-ok.yaml | 0 | - | 1.5 | - | |
| m4-pdb-min-zero.yaml | 0 | - | 1.5,2.5 | - | |
| m4-senha-em-args.yaml | 1 | 3.3 | 1.5 | - | |
| m4-senha-em-comentario.yaml | 0 | - | 1.5 | - | |
| m4-token-ttl-ok.yaml | 0 | - | 1.5 | - | |
| m2: execução 04 com trivy-config-data vazio | 0 | - | 1.5 | - | |

| Alvo | Código | Resumo |
|---|---|---|
| execucoes/01-escrita-fake-shop/manifests | 0 | Trivy: executado · BARRA: 0 · JUSTIFICAR: 0 · OK: 18 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 0 |
| execucoes/02-conferencia-nyx/nyx-barrado.yaml | 1 | Trivy: executado · BARRA: 11 · JUSTIFICAR: 2 · OK: 4 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 1 |
| execucoes/02-conferencia-nyx/nyx-corrigido.yaml | 0 | Trivy: executado · BARRA: 0 · JUSTIFICAR: 1 · OK: 17 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 0 |
| execucoes/03-escrita-encontros-tech/manifests | 0 | Trivy: executado · BARRA: 0 · JUSTIFICAR: 1 · OK: 14 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 3 |
| execucoes/04-escrita-fake-shop-stg/manifests | 0 | Trivy: executado · BARRA: 0 · JUSTIFICAR: 1 · OK: 14 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 3 |
| execucoes/05-conferencia-nyx-skill-atual/nyx-barrado.yaml | 1 | Trivy: executado · BARRA: 11 · JUSTIFICAR: 2 · OK: 4 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 1 |
| execucoes/05-conferencia-nyx-skill-atual/nyx-corrigido.yaml | 0 | Trivy: executado · BARRA: 0 · JUSTIFICAR: 1 · OK: 17 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 0 |
| fluxo-manual/05-correcoes-pos-revisao/values.yaml | 2 | ERRO: nenhum objeto de Kubernetes (apiVersion/kind) encontrado nos arquivos. |
| fluxo-manual/05-correcoes-pos-revisao/list.yaml | 1 | Trivy: executado · BARRA: 4 · JUSTIFICAR: 2 · OK: 5 · NAO_VERIFICADO: 4 · NAO_SE_APLICA: 3 |
| fluxo-manual/05-correcoes-pos-revisao/so-service.yaml | 0 | Trivy: executado · BARRA: 0 · JUSTIFICAR: 0 · OK: 4 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 14 |
| nyx-barrado --sem-trivy | 1 | barra vence incompleto: 1; sem barra: 3 |
| nyx-corrigido --sem-trivy | 3 | barra vence incompleto: 1; sem barra: 3 |

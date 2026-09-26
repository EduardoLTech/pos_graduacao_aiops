# Correção dos achados médios M2, M3 e M4

Os casos foram feitos em 2026-09-25 para reproduzir cada achado de `../../revisao-critica.md`
**antes** de corrigir. O script `rodar-casos.sh` gera as duas tabelas do mesmo jeito:

- `antes.md`: script depois da correção do M1, antes desta;
- `depois.md`: script corrigido.

A maioria dos casos em `casos/` sai do `fake-shop.yaml` da execução 04, que passa com
código 0, com uma mudança só em cada um. Os de PDB trocam o namespace para `orion-prod`
e sobem para 2 réplicas, para que a 2.5 se aplique.

| Caso | Esperado |
|---|---|
| `m2`: execução 04 com `trivy-config-data` vazio | código 0; a KSV-0125 vira informativo, não barra a 3.7 |
| `m3-latin1.yaml` | código 2 (converter para UTF-8), não 1 |
| `m3-utf16.yaml`, `m3-utf8-bom.yaml` | lidos; mesmo resultado do UTF-8 |
| `m3-utf16-com-latest.yaml` | 3.1 e 3.2 barram. Antes da cópia em UTF-8, o Trivy lia o UTF-16 sem achado nenhum e as duas saíam OK |
| `m3-crlf-varios-documentos.yaml` (CRLF, Deployment no 4º documento) | 3.1 e 3.2 barram. Pega o C1 da revisão do delta: com a cópia gravada por `write_text`, o Trivy só lia o 1º documento |
| `m4-senha-em-args.yaml` | 3.3 barra |
| `m4-args-sh-c.yaml` (`sh -c "... --db-password x"`) | 3.3 barra |
| `m4-args-parametros-ok.yaml` (`--token-ttl`, `--password-file`, `--passive`, `--no-password`, `--tokenizer`, `--secret-name=`, `--api-key-file`) | 3.3 não barra |
| `m4-env-expansao-ok.yaml` (`$(DB_PASSWORD)`) | 3.3 não barra |
| `m4-env-dolar-literal.yaml` (`API_TOKEN=$enh4!`) | 3.3 barra |
| `m4-args-com-expansao-ok.yaml` (`$(DB_PASSWORD)`) | 3.3 não barra |
| `m4-db-pwd.yaml` | 3.3 barra |
| `m4-token-ttl-ok.yaml` | 3.3 não barra |
| `m4-senha-em-comentario.yaml` | pendência em "Conferência que exige ler o projeto", sem barrar |
| `m4-pdb-min-zero.yaml`, `m4-pdb-max-100.yaml` | 2.5 JUSTIFICAR (a regra é recomendada) |
| `m4-pdb-min-um-ok.yaml` | 2.5 OK |

Os casos acrescentados depois da revisão do delta também aparecem em `antes.md`, rodados
com o script anterior às correções de M2 a M4. `m3-crlf-varios-documentos` barra ali
porque o script antigo passava o arquivo original ao Trivy. Nele, a 3.3 barra pelo
`TOKEN_TTL` herdado do caso de origem.

`trivy-direto.md` roda o Trivy sem o script sobre o mesmo manifesto em três gravações
(LF, UTF-16 e `\r\r\n`). É a prova de que o Trivy fica calado nas duas últimas.

Para rodar, a partir de `ticket-01-padrao-de-manifests/`:
`bash fluxo-manual/06-correcoes-medios/rodar-casos.sh skill/manifests-metacortex "Título"`

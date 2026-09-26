# Antes da correção (script pós-M1, 2026-09-25)

| Caso | Código | BARRA | JUSTIFICAR | NAO_VERIFICADO | Erro |
|---|---|---|---|---|---|
| m3-crlf-varios-documentos.yaml | 1 | 3.1,3.2,3.3 | 1.5 | - | |
| m3-latin1.yaml | 1 | - | - | - | UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe7 in position 11: invalid continuation byte |
| m3-utf16.yaml | 1 | - | - | - | UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte |
| m3-utf16-com-latest.yaml | 1 | - | - | - | UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte |
| m3-utf8-bom.yaml | 1 | 3.3 | 1.5 | - | |
| m4-args-com-expansao-ok.yaml | 0 | - | 1.5 | - | |
| m4-args-parametros-ok.yaml | 0 | - | 1.5 | - | |
| m4-args-sh-c.yaml | 0 | - | 1.5 | - | |
| m4-db-pwd.yaml | 0 | - | 1.5 | - | |
| m4-env-dolar-literal.yaml | 1 | 3.3 | 1.5 | - | |
| m4-env-expansao-ok.yaml | 1 | 3.3 | 1.5 | - | |
| m4-pdb-max-100.yaml | 0 | - | 1.5 | - | |
| m4-pdb-min-um-ok.yaml | 0 | - | 1.5 | - | |
| m4-pdb-min-zero.yaml | 0 | - | 1.5 | - | |
| m4-senha-em-args.yaml | 0 | - | 1.5 | - | |
| m4-senha-em-comentario.yaml | 0 | - | 1.5 | - | |
| m4-token-ttl-ok.yaml | 1 | 3.3 | 1.5 | - | |
| m2: execução 04 com trivy-config-data vazio | 1 | 3.7 | 1.5 | - | |

# Trivy direto, sem o script (2026-09-25, Trivy 0.74.0)

Mesmo manifesto (`:latest` + `runAsNonRoot: false`), três gravações. Conta as falhas (Status FAIL) que o Trivy acha.

| Arquivo | Falhas do Trivy |
|---|---|
| UTF-8, LF, Deployment no 4º documento | 3 |
| UTF-16 com BOM (casos/m3-utf16-com-latest.yaml) | 0 |
| UTF-8 com \r\r\n (o que a cópia com write_text gerava a partir de CRLF) | 0 |

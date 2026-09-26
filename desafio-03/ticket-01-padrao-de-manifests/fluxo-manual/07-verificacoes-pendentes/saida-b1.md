| cenario | esperado | obtido | traceback | ultima linha |
|---|---|---|---|---|
| token sem JSON | 3 | 3 | nao | `NAO VERIFICADO: Expecting value: line 1 column 1 (char 0)` |
| desafio sem realm | 3 | 3 | nao | `NAO VERIFICADO: 'realm'` |
| manifesto schema1 (sem config) | 3 | 3 | nao | `NAO VERIFICADO: manifesto sem config (schemaVersion 1: formato v1 nao suportado)` |
| indice com entrada sem platform | 0 | 0 | nao | `Codigo de saida: 0` |
| platform nulo em todas as entradas | 3 | 3 | nao | `NAO VERIFICADO: sem manifesto para linux/amd64` |
| config do blob com campos nulos | 0 | 0 | nao | `Codigo de saida: 0` |
| blob de config que nao e JSON | 3 | 3 | nao | `NAO VERIFICADO: GET app/blobs/sha256:cfg nao devolveu JSON` |
| Hub --tags com last_updated nulo | 0 | 0 | nao | `Codigo de saida: 0` |
| Hub --tags devolve HTML | 3 | 3 | nao | `NAO VERIFICADO: Expecting value: line 1 column 1 (char 0)` |
| registry responde 500 no /v2/ | 3 | 3 | nao | `NAO VERIFICADO: registry.exemplo/v2/ respondeu 500` |

Falhas: 0 de 10

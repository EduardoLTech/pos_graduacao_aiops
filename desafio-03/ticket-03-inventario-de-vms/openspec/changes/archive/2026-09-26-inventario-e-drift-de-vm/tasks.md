## 1. Estrutura do projeto

- [x] 1.1 Criar `pyproject.toml` com dependências (paramiko, PyYAML) e pytest como dependência de teste; ponto de entrada de linha de comando
- [x] 1.2 Criar o pacote `inventario_vm/` com os módulos do design (D1) e `baseline.yaml` copiado do enunciado
- [x] 1.3 Documentar no README do ticket como criar o ambiente, rodar a ferramenta e rodar os testes

## 2. Baseline e linha de comando

- [x] 2.1 `baseline.py`: carregar e validar `baseline.yaml` (versão 1, 11 regras conhecidas, severidades) com testes de arquivo inválido
- [x] 2.2 `cli.py`: parâmetros obrigatórios e opcionais, validação de fingerprint esperado, erros de uso com código 2 sem conectar, mensagens que citam o parâmetro e nunca o valor
- [x] 2.3 `cli.py`: precedência dos códigos de saída (2, 3, 1, 4, 0) com teste de tabela

## 3. Conexão

- [x] 3.1 `conexao.py`: carga da chave por caminho, passphrase como erro de uso, autenticação sem agente e sem chaves padrão
- [x] 3.2 Política de chave de host: registrar algoritmo e fingerprint SHA256; comparar com o fingerprint esperado antes da autenticação
- [x] 3.3 Classificação de falha por tipo de exceção (nome, sem resposta, recusa, chave recusada, não-SSH, chave de host divergente) com orçamento de 15 s
- [x] 3.4 Execução de leitura com limite de 20 s e 1 MiB, e detecção de conexão caída durante a coleta
- [x] 3.5 Silenciar log do paramiko e traceback de thread; captura final no `main` sem stack trace e sem caminho da chave

## 4. Coleta e inventário

- [x] 4.1 `coleta.py`: tabela fixa de leituras (D2) com prefixo `LC_ALL=C` e desfecho lida / sem privilégio / falha
- [x] 4.2 Script constante de fontes de chave (D4) e reconhecimento de "sem privilégio" por fato do host (D3)
- [x] 4.3 `inventario.py`: interpretação de os-release, kernel, unidades, swap, portas, chaves (opções, comentário com espaços, linhas ignoradas), sshd e ntp, com ordem estável
- [x] 4.4 Gravar no laboratório as saídas brutas reais das leituras nos dois estados e usá-las como fixtures dos testes de interpretação

## 5. Regras

- [x] 5.1 `regras.py`: comparação numérica de versões e classificação de bind interno/público
- [x] 5.2 As 11 regras com os três vereditos, motivo, `encontrado` parcial e severidade vinda do baseline, um teste por cenário das specs
- [x] 5.3 Resumo e `por_severidade` com as três severidades sempre presentes

## 6. Relatório

- [x] 6.1 `relatorio.py`: montagem única do relatório; JSON com a forma do enunciado mais campos adicionais
- [x] 6.2 Markdown no esqueleto do PRD P15, ordem de desvios por severidade, "Nenhum." em seção vazia
- [x] 6.3 Neutralização de texto do host (controle, `|`, quebra de linha, tamanho) com o caso hostil do P28
- [x] 6.4 Gravação do JSON por arquivo temporário e renomeação, sem tocar o arquivo em erro

## 7. Laboratório (custo em nuvem: criar a VM exige confirmação de quem opera)

- [x] 7.1 `laboratorio/criar.sh`: VPC própria, firewall só 22 do IP do operador, VM sem conta de serviço, `block-project-ssh-keys`, `enable-oslogin=FALSE`
- [x] 7.2 `laboratorio/preparar-conforme.sh` e `laboratorio/preparar-desvios.sh`
- [x] 7.3 `laboratorio/destruir.sh`
- [x] 7.4 Conferir na VM os itens não verificados do PRD: grupos do usuário de coleta, `ssh.socket`, chrony × timesyncd, leitura de `sshd -T` sem root, log do paramiko citando a chave

## 8. Evidência e validação

- [x] 8.1 Execução contra o host conforme: Markdown, JSON e código de saída
- [x] 8.2 Execução contra o host com desvios
- [x] 8.3 Host inalcançável em três variantes (endereço errado, chave recusada, SSH fora do ar) e fingerprint divergente
- [x] 8.4 Duas execuções seguidas comparadas, e prova de que o host não mudou
- [x] 8.5 Busca do conteúdo e do caminho da chave em todas as saídas (PRD I2)
- [x] 8.6 Comentário de chave hostil no host (P28)
- [x] 8.7 Evidência publicada com valores sintéticos (IP, fingerprint, comentários) revisada antes do commit

## 9. Fechamento

- [x] 9.1 Atualizar o TRD (módulos, estrutura de pastas, testes) e corrigir o PRD onde a implementação mostrou erro
- [x] 9.2 Escrever a curadoria: onde o documento precisou ser corrigido e o que o agente entendeu diferente
- [x] 9.3 Destruir a VM e registrar a destruição
- [x] 9.4 Arquivar a change no OpenSpec

# relatorio Specification

## Purpose
Os dois formatos do relatório, JSON e Markdown, gerados do mesmo dado, e a neutralização do texto vindo do host (PRD-0001 P6, P15, P28, I7).

## Requirements
### Requirement: JSON e Markdown da mesma coleta
A ferramenta MUST emitir o Markdown no stdout e, quando o operador informar um arquivo, o JSON
nesse arquivo, ambos da mesma coleta: `coletado_em` idêntico e os mesmos vereditos. Sem arquivo
informado, só o Markdown é produzido; o código de saída é o mesmo nos dois casos (PRD P6).

#### Scenario: Os dois formatos
- **WHEN** o operador informa um arquivo para o JSON
- **THEN** o stdout traz o Markdown, o arquivo traz o JSON, e os dois têm o mesmo `coletado_em`
  e os mesmos vereditos

#### Scenario: Só Markdown
- **WHEN** nenhum arquivo JSON é informado
- **THEN** só o Markdown é produzido, e nenhum JSON sai no stdout

### Requirement: Forma do JSON
O JSON MUST seguir a forma do exemplo do enunciado, com os blocos `host`, `inventario`,
`conformidade` e `resumo`; campos adicionais (`chave_de_host`, `motivo`, `conta`,
`chaves_ssh_fontes_nao_lidas`) acrescentam e não renomeiam. Severidade sai sem acento
(`critico`, `medio`). `encontrado` MUST levar o tipo do dado (booleano, texto, lista de nomes ou
lista de `{porta, bind}`); a frase para o leitor MUST NOT ir para o JSON.

#### Scenario: Entrada de desvio no JSON
- **WHEN** `kernel.versao_minima` é desvio
- **THEN** a entrada tem `regra`, `esperado`, `encontrado`, `veredito: desvio` e `severidade:
  medio`

#### Scenario: encontrado comparável com esperado
- **WHEN** o host tem swap de 4 GiB
- **THEN** a entrada de `swap.habilitado` traz `"esperado": false` e `"encontrado": true` no
  JSON, e o Markdown mostra `true (4G)`

### Requirement: Esqueleto do Markdown
O Markdown MUST seguir o esqueleto literal do PRD P15, com as três seções sempre presentes,
nesta ordem, e "Nenhum." quando a seção não tem itens:
- título de nível 1 `Inventário — <hostname> (<endereco>)`;
- linha `Coletado em <AAAA-MM-DD hh:mm> UTC · baseline v<versao> · chave de host <algoritmo>
  <fingerprint>`;
- seção de nível 2 `Desvios`, tabela com colunas Severidade, Regra, Esperado, Encontrado;
- seção de nível 2 `Não verificado`, tabela com colunas Regra, Motivo;
- seção de nível 2 `Conforme`, com as regras separadas por ` · `.

Desvios vêm em ordem de severidade (crítico, alto, médio) e, dentro dela, na ordem do baseline;
as demais seções seguem a ordem do baseline. Severidade sai com acento (`crítico`, `médio`)
(PRD P15).

#### Scenario: Ordem dos desvios
- **WHEN** há desvios em `kernel.versao_minima` (médio) e `swap.habilitado` (crítico)
- **THEN** a linha de `swap.habilitado` vem antes da de `kernel.versao_minima`

#### Scenario: Nenhum desvio
- **WHEN** nenhuma regra é desvio
- **THEN** a seção Desvios mostra "Nenhum." no lugar da tabela

### Requirement: Texto do host é neutralizado
Todo texto vindo do host MUST ser tratado como dado: caracteres de controle MUST ser escapados de
forma visível, `|` e quebra de linha MUST ser neutralizados no Markdown, o texto MUST ser
limitado em tamanho, e o JSON MUST NOT conter caractere de controle cru (PRD P28, I7).

#### Scenario: Comentário de chave hostil
- **WHEN** uma chave tem comentário com `\x1b[2K`, quebra de linha e `| x | conforme |`
- **THEN** o Markdown mostra o texto de forma literal e visível, as tabelas mantêm o número de
  linhas correto, e o JSON não traz caractere de controle cru


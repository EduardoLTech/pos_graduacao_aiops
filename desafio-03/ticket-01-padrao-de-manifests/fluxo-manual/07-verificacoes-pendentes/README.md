# Verificações que tinham ficado abertas (2026-09-25)

Depois da revisão focada do delta, seis afirmações sobre a skill seguiam sem prova.
Esta pasta guarda como cada uma foi fechada, ou por que não foi.

| Item | Resultado | Evidência |
|---|---|---|
| B1: registry que responde fora do formato | **Confirmado.** 10 de 10 cenários sem traceback, com o código certo (3 quando a resposta está torta, 0 quando só falta campo opcional) | `b1_registry_simulado.py`, `saida-b1.md` |
| Linux | **Confirmado.** Com Python 3.13.15 e Trivy 0.74.0, a saída é idêntica à do Windows nos 30 casos da regressão (37 linhas de tabela). Só mudam o separador de caminho e a ordem do glob. `inspecionar_imagem.py` também foi testado no Linux, contra Docker Hub e `registry.k8s.io` | `linux.Dockerfile`, `regressao.sh`, `regressao-windows.md`, `regressao-linux.md` |
| `%TEMP%` em outro drive | **Confirmado nos dois sentidos**, com um drive X: criado por `subst`: `%TEMP%` em X: com a skill em C:, e a skill em X: com `%TEMP%` em C:. Nos dois, o Trivy leu a cópia e o resultado foi o de referência (11 BARRA, código 1). A letra do drive só se perde no `--config-data`, que já vai relativo | comando abaixo |
| O frontmatter sozinho concede as permissões? | **Depende de quem invoca.** Pelo usuário (`/manifests-metacortex`): sim, 0 negações. Pelo modelo (ferramenta Skill) numa sessão `claude -p`: não, e as ferramentas da lista foram negadas | `../../execucoes/06-conferencia-nyx-so-frontmatter/` e a seção abaixo |
| O matcher do `allowed-tools` casa `python -c "<código>" <script>.py`? | **Não verificado.** O classificador de segurança do agente bloqueou o teste | `matcher-prompt.txt` não foi gravado |
| macOS | **Não verificado.** Não havia máquina disponível | — |

## Frontmatter: o que foi medido

A documentação do Claude Code diz que o `allowed-tools` concede as ferramentas listadas
durante o turno em que a skill é invocada, "por você ou pelo Claude", inclusive em `-p`.
Medido no Claude Code 2.1.283, Windows, `--permission-mode default`, sem nenhuma regra
de allow nas settings:

| Invocação | Formato do `allowed-tools` | Negações | O que foi negado |
|---|---|---|---|
| modelo (Skill), conferência completa, execução 06 | vírgula (o da skill) | 7 | Bash do script (3), Write (2), Read/Glob fora do diretório (2) |
| modelo (Skill), preflight + Write | vírgula · espaço · lista YAML | 6 · 13 · 3 | Bash do script em todas; Write na de espaço |
| usuário (`/manifests-metacortex`), preflight + Write | lista YAML | 0 | — |
| usuário | vírgula | 1 | a chamada pela ferramenta PowerShell, que não está na lista; o agente refez pelo Bash e passou |
| usuário | espaço | 0 | — |

Conclusões:
- O formato da lista não importa. O que muda o resultado é quem invoca a skill.
- Quando o disparo é automático numa sessão sem interação, a permissão precisa vir de
  fora: `--allowedTools` (como nas execuções 04 e 05) ou regra nas settings. Em sessão
  interativa, o esperado é que a chamada sem permissão vire pergunta ao usuário, e não
  negação. **Isso não foi medido.**
- Amostra pequena: uma versão do Claude Code (2.1.283), uma a três sessões por
  variante. A execução 06 está versionada. Os seis testes curtos rodaram num diretório
  temporário, e as transcrições deles ficaram fora do repositório.
- No Windows o agente às vezes escolhe a ferramenta PowerShell. Por isso o `SKILL.md`
  agora diz para usar a ferramenta Bash.
- Na variante "espaço", com o script negado, o agente tentou gravar
  `.claude/settings.json` para liberar a própria permissão. O Write foi negado. É o tipo
  de contorno que o envelope precisa segurar, e segurou.
- Na execução 06, sem conseguir rodar o script, o agente leu a conferência da execução
  05 na pasta vizinha. A saída dela não vale como conferência; a execução vale só como
  medida de permissão.

## Como reproduzir

```sh
# a partir de ticket-01-padrao-de-manifests/
python fluxo-manual/07-verificacoes-pendentes/b1_registry_simulado.py skill/manifests-metacortex/scripts/inspecionar_imagem.py
bash fluxo-manual/07-verificacoes-pendentes/regressao.sh "Windows"
docker build -f fluxo-manual/07-verificacoes-pendentes/linux.Dockerfile -t conferir-linux fluxo-manual/07-verificacoes-pendentes
docker run --rm -v "$PWD:/t:ro" -w /t conferir-linux bash fluxo-manual/07-verificacoes-pendentes/regressao.sh "Linux"
```

`%TEMP%` em outro drive (PowerShell):

```powershell
subst X: <pasta-vazia>
$env:TEMP="X:\"; $env:TMP="X:\"
python skill\manifests-metacortex\scripts\conferir_manifests.py execucoes\05-conferencia-nyx-skill-atual\nyx-barrado.yaml
subst X: /D
```

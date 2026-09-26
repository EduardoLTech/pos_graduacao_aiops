# Inventário — construct-node-14 (203.0.113.10)
Coletado em 2026-09-26 16:04 UTC · baseline v1 · chave de host ssh-ed25519 SHA256:Exemp1oDeFingerprintSinteticoParaEvidencia0

## Desvios

| Severidade | Regra | Esperado | Encontrado |
|---|---|---|---|
| crítico | swap.habilitado | false | true (1G) |
| crítico | portas_em_escuta.publicas_permitidas | 22 | 111 em 0.0.0.0, 111 em :: |
| crítico | portas_em_escuta.somente_rede_interna | 9100 | 9100 em * |
| crítico | chaves_ssh.emitidas_por | metacortex-platform | neo\x1b[2K \| x \| conforme \|, neo@laptop, legado@fornecedor |
| alto | servicos.ativos | ssh, containerd, node_exporter, chrony | ausente: chrony |
| alto | servicos.proibidos | telnet.socket, rpcbind.socket | ativo: rpcbind.socket |
| médio | ntp.sincronizado | true | false |

## Não verificado

| Regra | Motivo |
|---|---|
| ssh.login_de_root | exige privilégio que o usuário da coleta não tem |

## Conforme
so.distribuicao · so.versao_minima · kernel.versao_minima

A causa é o limite de memória do container: 24Mi é pouco demais para a API. O kernel mata o processo cerca de 2 a 4 segundos depois de cada partida.

O quadro é pior do que o chamado descreve. A API não está só reiniciando: as duas réplicas estão em CrashLoopBackOff, com 0/1 pronto cada e 4 reinícios em 2m33s. Ou seja, a API do kube-news está fora do ar agora.

```
# Triagem — nyx-prod/nyx-api (kube-news)
Sintoma declarado: API reinicia sozinha
Camada da causa: container
Causa: o limite de memória de 24Mi é pequeno demais para a API Node do kube-news,
       e o kernel mata o processo por OOM logo depois de cada partida.
Evidência:
  - estado: pod nyx-api-cb9d64767-7vxz9 · lastState.terminated · reason=OOMKilled,
            exitCode=137, startedAt 23:19:45 → finishedAt 23:19:47 (2s)
            pod nyx-api-cb9d64767-cbl5d · mesmo quadro · OOMKilled/137, 23:19:37 → 23:19:41 (4s)
            as duas réplicas estão em CrashLoopBackOff, restartCount=4, ready=false
  - spec:   container api · resources.limits.memory=24Mi (requests.memory=16Mi)
Funciona ao lado: nyx-postgres-c8886cfc8-pfm8g · 1/1 Running, 0 reinícios, no mesmo nó.
                  Isso descarta o nó e o banco.
Correção sugerida (não aplicada): no Deployment nyx-api, subir resources.limits.memory
                  para algo compatível com Node (ponto de partida: 256Mi de limite e 128Mi de request).
                  Depois ajustar pelo consumo medido.
Achados laterais:
  - DB_PASSWORD está em texto puro no env do Deployment. Deveria vir de um Secret.
  - Não há livenessProbe, só readinessProbe.
Não verificado: quanto a API consome de fato (precisaria do metrics-server).
                O log anterior veio vazio, o que é esperado quando o processo morre em 2s.
Caminho: kubectl_get pods (wide) → kubectl_get pod 7vxz9 (json) → kubectl_logs --previous
         → kubectl_get pod cbl5d (yaml)
```

Não alterei nada no cluster. A correção precisa ser aplicada por alguém.

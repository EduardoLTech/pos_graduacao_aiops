# Exercício 02 - Framework RFT

## 1. Prompt
O prompt completo está registrado no arquivo prompt.txt e a resposta no arquivo JanelaContexto.md.

## 2. Modelo
O modelo utilizado é o **Gemini 3.1 Pro (low)**, rodando na IDE Antigravity, escolhido por ser uma tarefa que requer um pouco mais de raciocinio para a geracao de shell script que envolve conexao com serviçoes na AWS.

## 3. Output
A resposta gerada pelo modelo está no arquivo JanelaContexto.md.

## 4. Justificativa
Os componentes do framework estão no prompt separados por:
* **Role (Papel):** Ao definir a IA como SRE senior e especialista em postgresql, aws e shell script, forcei o modelo a ser um especialista no assunto para uma geração mais precisa do shell script de backup.
* **Task (Tarefa):** Passei todos os dados crus e especificações técnicas do problema, como credenciais de banco, bucket AWS, SO, etc.
* **Format (Formato):** Garantir que a saída seja um arquivo completo, comentado e pronto para ser usado.

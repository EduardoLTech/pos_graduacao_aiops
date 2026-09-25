# Instalar o Trivy

Confira primeiro: `trivy --version`. A skill foi validada com a 0.74.0.

- macOS: `brew install trivy`
- Debian/Ubuntu: repositório oficial (https://trivy.dev/latest/getting-started/installation/)
- Windows: baixe `trivy_<versao>_windows-64bit.zip` da página de releases do
  `aquasecurity/trivy`, confira o SHA-256 contra `trivy_<versao>_checksums.txt` e ponha
  o `trivy.exe` num diretório do PATH.

Instalar software na máquina do usuário é decisão dele: proponha o comando e peça
confirmação. No primeiro uso, o Trivy baixa o bundle de checagens (precisa de rede).
Se não houver rede nem Trivy, rode o script com `--sem-trivy` e reporte as regras 2.1,
3.1, 3.2 e 3.6 como não verificadas.

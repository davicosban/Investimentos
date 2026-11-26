# Painel Investimentos

App pessoal para acompanhar a bolsa brasileira e americana e calcular rentabilidade de renda fixa.

- `site/`: o app (página única) e os dados (`br.json`, `us.json`, `hist.json`).
- `scripts/atualizar.py`: busca dados novos (Fundamentus, brapi, Nasdaq, Yahoo Finance, Banco Central).
- `.github/workflows/atualizar.yml`: roda o script todo dia útil às 18h30 (Brasília) e publica no GitHub Pages.

Para atualizar na hora: aba **Actions** → *Atualizar dados e publicar* → **Run workflow**.

Não é recomendação de investimento. Taxas de bancos na calculadora são exemplos; as do Tesouro Direto são de 26/11/2026.

## App para Windows

`desktop/` é um app Electron que abre o site numa janela própria, sem a barra de título do Windows.
O instalador é gerado pelo workflow *Gerar app para Windows* e fica em **Releases** (`Painel-Investimentos-Setup.exe`).

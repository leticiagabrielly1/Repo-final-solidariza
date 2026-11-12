# Correções de gráficos e estoque

- Três gráficos mensais no painel administrativo: quantidade de doações, valores Pix simulados e desperdício. Os dados são consultados no SQLite, sem inventar movimentações.
- Estoque inicial de 50 unidades por produto para cada unidade que estava completamente zerada e não possuía movimentos físicos. O banco incluído no ZIP foi corrigido.
- Unidades que já têm movimentos físicos não recebem reposição automática.
- Dados de Pix continuam identificados como simulação.

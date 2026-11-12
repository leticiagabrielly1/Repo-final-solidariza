# Atualização de novembro — Rede Solidariza

Base utilizada: `Rede_Solidariza_com_Rute.zip` (contém a assistente). A segunda versão enviada é uma cópia anterior sem assistente; para preservar funcionalidades, a versão com assistente foi usada.

- Logo original aplicada pelo template base em todas as telas; favicon PNG em todas as páginas.
- Assistente identificada como Sofia e avatar fornecido, preservando as rotas e integrações existentes.
- Tela de autenticação dividida já existente foi mantida, agora com a logo original.
- Estoque oculto da navegação dos beneficiários e bloqueado para esse perfil na rota de estoque.
- Estoque inicial de 50 unidades por produto e unidade, apenas na primeira inicialização; retiradas posteriores não são repostas automaticamente.
- Painel administrativo com totais e histórico de registros Pix simulados, evolução mensal, e metas por unidade salvas no SQLite.
- QR Code e chave demonstrativos não bancários, explicitamente rotulados como simulação.
- Permissões, logins e senhas existentes preservados.

## Limites importantes

Os registros Pix não são pagamentos reais e não devem ser tratados como receita. O projeto não registra transferências bancárias verificadas nem valores financeiros efetivamente destinados a beneficiários; esses indicadores aparecem como indisponíveis, sem inventar números. Indicadores de desperdício e crescimento comparativo ainda exigem uma fonte de dados operacional consistente. O cadastro de metas financeiras é demonstrativo.

A execução automatizada dos testes não foi possível neste ambiente por falta do pacote Flask. Instale as dependências com `pip install -r requirements.txt` e execute os testes com `python -m unittest discover -s tests` antes de publicar.

# Rede Solidariza — acesso administrativo pelo site e DBeaver

1. Instale as dependências e execute o projeto normalmente.
2. Cadastre um usuário comum pelo site.
3. No próprio computador em que o servidor está rodando, abra `/configurar-primeiro-admin` e informe o CPF da conta, a unidade e o CEP real dela. Esta rota funciona somente no acesso local e apenas enquanto não existir administrador. Não exponha o servidor de desenvolvimento à internet.
4. Entre em `/login-admin` com **usuário = CEP da unidade** e **senha inicial = o mesmo CEP**. Será obrigatório escolher uma nova senha (12+ caracteres).
5. O primeiro administrador pode vincular outras unidades em `/admin/vincular`, usando contas previamente cadastradas.

## Banco de dados no DBeaver

O banco é **SQLite**, arquivo `instance/rede.db`, criado automaticamente pelo Flask. No DBeaver escolha Nova conexão > SQLite > selecione esse arquivo > Concluir. As tabelas `usuarios`, `estoque`, `movimentos`, `entregas`, `administradores_pontos`, `unidades_admin` e `pix_cobrancas` estarão disponíveis. O DBeaver não é um tipo de banco, é um gerenciador.

**Atenção:** o CEP é público e só serve como senha inicial de demonstração; troque-a no primeiro acesso. Não há CEPs reais pré-carregados: informe os CEPs verificados das unidades. Não coloque a pasta `instance` com dados reais em repositórios públicos.

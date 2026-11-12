# Rede Solidariza — Flask

Interface inspirada na referência enviada: login em duas colunas, azul para beneficiários, verde para doadores, amarelo nos botões e menu lateral. HTML, CSS e JavaScript locais, sem CDN. Os ícones de produtos usam emojis e podem variar conforme o dispositivo. O logotipo é uma interpretação tipográfica, não o arquivo original do projeto gráfico.

## Executar

Requer Python 3.10 ou superior. Extraia o ZIP e abra a pasta `rede-solidariza` no VS Code. No terminal dentro dessa pasta:

```sh
python -m pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000. No Windows, se `python` não funcionar, use `py`. No Linux, pode ser necessário usar `python3` ou criar um ambiente com `python3 -m venv .venv` e ativá-lo com `source .venv/bin/activate` antes de instalar.

Crie sua conta na aba Cadastrar. Não há uma conta ou senha padrão. Use dados fictícios para os testes. O banco `instance/rede.db` e a chave de sessão são criados automaticamente e persistem quando o servidor é reiniciado. Não publique a pasta instance no GitHub. A aplicação não importa automaticamente dados do antigo programa de terminal.

## Exemplos de teste

- Beneficiário: 4 moradores, 1 criança, renda total de R$ 1.000 → renda por pessoa R$ 250, cesta + kit de higiene.
- Beneficiário: 2 moradores, renda R$ 1.000 → cesta, sem kit extra.
- Doador: 2 moradores, renda R$ 2.000 → área de doações.
- CPF demonstrativo: qualquer sequência de 11 números ainda não cadastrada. O sistema valida o formato, não os dígitos verificadores nem a identidade.
- Telefone: 10 ou 11 números. Senhas de 8 a 128 caracteres, armazenadas como hash.

## Fluxos disponíveis

Cadastro → resultado da regra escolar → painel. Login/logout; beneficiário monta uma cesta e pede roupas; doador registra alimentos, roupas e valores. Pontos de coleta, consulta de estoque, comprovantes imprimíveis e histórico individual. Itens e cadastros persistem no SQLite. Movimentações de estoque são transacionais: se faltar um item, todo o registro é desfeito.

### Regras preservadas e correções

- Renda por pessoa **a partir de R$ 800** define Doador, como o primeiro `if` original. Abaixo de R$ 800 define Beneficiário. Não há faixa de "não tem direito" na regra original.
- Até R$ 300 por pessoa: kit extra de higiene (1 de cada produto), agora descontado do estoque.
- Infantil: 20 unidades; Emergencial: 18; Nutricional: 15. Com crianças: +5 unidades. Mínimo de 1 de cada produto obrigatório. Unidades, e não apenas tipos de produto, contam para o limite.
- Uma cesta por cadastro nesta versão. Pedidos de roupas são independentes e não impedem montar a cesta.
- Os pontos e os estoques iniciais são os exemplos do programa enviado. A análise de renda é uma simulação educacional, sem vínculo com programas públicos.
- Doações de itens atualizam imediatamente o estoque de demonstração. Não há confirmação logística de entrega.
- Valores são apenas registros, sem cobrança, Pix, gateway ou validação de pagamento. O painel mostra o total individual. Não há doação anônima nesta versão autenticada.
- O painel lista somente o histórico da própria conta. A listagem de pessoas é restrita a administradores e não inclui CPF, senha ou renda. Para promover uma conta já criada, execute localmente `python -m flask --app app tornar-admin` e informe o CPF dessa conta. Depois entre novamente e abra Cadastros no menu.

## Rute, assistente virtual

Botão flutuante disponível para visitantes, doadores, beneficiários e administradores. Veja [RUTE.md](RUTE.md).

## Organização

- rute.py: assistente virtual Rute (intenções, respostas por perfil e camada opcional de IA).
- static/rute.js, static/rute.css e static/editorial.css: widget da Rute e refinamento visual.
- app.py: rotas, regras, autenticação e SQLite.
- templates/: páginas Jinja e base compartilhada.
- static/style.css: identidade visual, layout responsivo e impressão.
- static/app.js: menu móvel, exibição de senha, busca de produtos e resumo da cesta.
- tests/test_app.py: testes dos fluxos e das transações, executáveis com `python -m unittest discover -s tests -v`.

## Limites desta entrega

Aplicação local para estudo. Não inclui login Google, recuperação de senha por e-mail, consultas externas, análise social real, notificações, pagamento, endereços reais ou agendamento de retiradas. Esses elementos não foram simulados com botões sem função. Antes de uma implantação pública com dados reais, é necessário adicionar controle de tentativas de login, HTTPS, política de privacidade e retenção, rotinas de backup e administração operacional. O servidor inicia sem debug e escuta somente no computador local.

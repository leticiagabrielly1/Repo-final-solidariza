# Sofia, assistente virtual da Rede Solidariza

A Sofia aparece como um botão flutuante no canto da tela em **todas as páginas**. Ela se adapta a quem está usando:

| Perfil | O que a Sofia faz |
|---|---|
| **Visitante** (login, cadastro, login admin) | Explica a rede, orienta o cadastro e as regras de perfil. |
| **Doador** | Passo a passo para doar alimentos, roupas e Pix; mostra o que está em falta no ponto; resume registros, valores e doações pendentes. |
| **Beneficiário** | Tipos de cesta e limites (já com o extra de crianças), kit de higiene, pedido de roupas, código da cesta e retirada. |
| **Administrador** | Entregas pendentes da unidade, como confirmar, itens com estoque baixo, ajuste de estoque, doações/Pix, unidades e acessos (só o administrador principal), troca de senha. |

Cada resposta pode trazer **botões de atalho** (por exemplo, "Montar minha cesta →") e **sugestões** de próximas perguntas.

## Como funciona

1. **Regras (sempre ativas, sem internet e sem custo).** `rute.py` reconhece a intenção da pergunta e responde com as regras reais do projeto e com números da própria conta ou unidade. Se ela não souber, diz que não sabe em vez de inventar.
2. **Modelo de linguagem (opcional).** Só entra quando nenhuma regra reconhece a pergunta **e** existe a variável `ANTHROPIC_API_KEY`. Se a chamada falhar, a Sofia volta para a resposta das regras.

```sh
# Opcional: ativar a camada de IA para perguntas livres
export ANTHROPIC_API_KEY="sua-chave"
export RUTE_MODELO="claude-haiku-5-5"   # opcional; este é o padrão
python app.py
```

Sem a chave, tudo funciona normalmente (modo regras).

## Privacidade e segurança

- A Sofia usa **apenas os dados da própria conta e da própria unidade**. Nunca CPF, senha, renda, telefone ou endereço. Esses dados também **não são enviados** à camada de IA (há teste automatizado para isso).
- O endpoint `POST /rute/mensagem` exige o token CSRF (cabeçalho `X-CSRF-Token`) e tem limite de 20 mensagens por minuto por IP e conta.
- As respostas são desenhadas na tela com `textContent` (nunca `innerHTML`), então texto digitado não vira HTML.
- A conversa fica só no navegador (`sessionStorage`, por aba) e é apagada ao clicar em **Sair da conta**.
- A Sofia não faz pagamentos nem altera dados: ela orienta e leva às páginas certas.

## Arquivos

| Arquivo | Função |
|---|---|
| `rute.py` | Cérebro da Sofia: intenções, respostas por perfil, camada opcional de IA. Não depende do Flask. |
| `app.py` | Rota `/rute/mensagem`, montagem do contexto (`rute_contexto`) e limite de uso. |
| `templates/_rute.html` | Marcação do widget (incluída em `base.html`). |
| `static/rute.js` / `static/rute.css` | Comportamento e visual da conversa. A cor segue o perfil (azul, verde e vinho). |
| `static/editorial.css` | Refinamento visual global (tipografia de destaque e acabamento). Não altera layout. |
| `tests/test_rute.py` | 19 testes: perfis, CSRF, privacidade, limite de uso e camada de IA. |

## Como ensinar algo novo à Sofia

Em `rute.py`: crie uma função `_r_algo(c)` que devolve `(texto, ações, sugestões)` e registre uma linha em `INTENCOES` com os perfis que podem ver aquela resposta e as expressões que a ativam. Ações são `(rótulo, endpoint, argumentos)`; o `app.py` as converte em links.

## Testes

```sh
python -m unittest discover -s tests -v
```

## Segurança do repositório (atenção)

Ao auditar o projeto, encontrei itens que **não devem estar em um repositório público**:

- `instance/secret.key` (chave de sessão) e `instance/rede.db` (banco com dados) estão versionados.
- As senhas iniciais dos administradores estão escritas no `app.py` e em `ALTERACOES.md`.

Recomendado: adicionar o `.gitignore` incluído, remover esses arquivos do Git (`git rm --cached -r projeto_admin_vermelho/*/instance`), **gerar uma nova `secret.key`**, trocar as senhas dos administradores e, idealmente, ler as senhas iniciais de variáveis de ambiente. Como já estiveram públicos, considere-as comprometidas.

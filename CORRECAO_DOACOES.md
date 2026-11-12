# Correção do painel administrativo

- Corrigido `templates/admin_painel.html` (estava com código Python em vez de HTML).
- Adicionada a rota `/admin/doacoes`, com filtros `?tipo=pix`, `?tipo=roupas` e `?tipo=alimentos`.
- Adicionado o link de doações no menu lateral do administrador.
- Cada administrador vê somente doações da unidade vinculada ao seu CEP.
- O Pix mostra o status da cobrança registrada; não confirma pagamento bancário automaticamente.

## Como instalar

1. Faça uma cópia da pasta atual e preserve `instance/rede.db` (contém os dados).
2. Extraia este ZIP e substitua os arquivos de código e templates.
3. Se quiser manter as doações antigas, copie o banco `instance/rede.db` da pasta antiga para `instance/` da pasta nova com o servidor desligado.
4. Instale `pip install -r requirements.txt` e execute `python app.py`.
5. Acesse `/login-admin`, depois `/admin` e `/admin/doacoes`.

# Rede Solidariza — acessos administrativos automáticos

1. Instale dependências: `pip install -r requirements.txt`.
2. Execute `python app.py`.
3. Na primeira execução, o sistema cria automaticamente **três administradores**, um por CEP das unidades RN verificadas.
4. Abra **`instance/ACESSOS_ADMIN_INICIAIS.txt`** no computador onde executou o sistema. Esse arquivo contém os CEPs e as senhas iniciais individuais. **Não publique nem compartilhe o arquivo.**
5. Entre em http://127.0.0.1:5000/login-admin e troque a senha no primeiro acesso.

Unidades pré-configuradas: Alecrim (59030350), Zona Norte (59110185), Centro (59025030). Os 27 estados estão disponíveis no seletor, mas **as unidades dos outros estados não foram inventadas nem cadastradas**. Para novas unidades, é necessário informar CEP real e endereço. Cada novo acesso deve ter senha inicial própria.

Se já houver um banco antigo em `instance/rede.db`, a rotina apenas cria contas que ainda não existam; ela não substitui senhas antigas.

**Segurança:** as senhas são geradas aleatoriamente e armazenadas no banco como hash. O arquivo local com as senhas iniciais deve ser guardado com cuidado e apagado após a troca das senhas. Não utilize esse protótipo como sistema público de doações sem revisão de segurança.

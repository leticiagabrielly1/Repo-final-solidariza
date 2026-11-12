# Configuração das unidades e Pix

1. Instale dependências: `python -m pip install -r requirements.txt`
2. Edite `senacs.json` com **unidades reais e autorizadas**, endereço completo e latitude/longitude verificadas. Os nomes atuais são exemplos NÃO VERIFICADOS. A localização depende de permissão do navegador e HTTPS (ou localhost).
3. Para receber Pix, configure as variáveis de ambiente `PIX_CHAVE`, `PIX_RECEBEDOR` e `PIX_CIDADE`. Não publique sua chave sem autorização.
4. Para criar administrador de unidade, cadastre usuário normalmente e execute `flask --app app tornar-admin`, informando CPF e nome exato do ponto. Cada administrador tem apenas uma unidade.
5. O prazo de entrega de itens é de 7 dias; o estoque só aumenta quando o administrador confirma.
6. O QR Code é um BR Code Pix estático com vencimento **apenas no sistema** após 5 minutos; ele não impede pagamento bancário posterior. O site NÃO verifica pagamentos e NÃO marca doações financeiras como pagas. Para Pix dinâmico com expiração e confirmação real, integre um PSP/banco com API e webhook autenticado.
7. Antes de produção, configure HTTPS, backups, auditoria, privacidade/LGPD e autorizações formais das unidades.

### Estados e painel administrador
Na página /pontos, o visitante seleciona o estado; somente as unidades daquele estado aparecem. Para cadastrar unidades de outros estados, acrescente objetos em senacs.json com nome, estado (sigla UF), endereco, latitude e longitude verificados. O painel fica em /admin e exige login de administrador vinculado a uma unidade. Para atribuir acesso, execute `flask --app app tornar-admin`. Cada administrador visualiza somente os registros da própria unidade.

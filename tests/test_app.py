import os
import unittest
import tempfile
import json
from pathlib import Path
from unittest import mock
from app import app, db, init_db, PONTOS

class Flows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True,DATABASE=str(Path(self.tmp.name)/'test.db'))
        with app.app_context():
            init_db()
            # O sistema cria o estoque zerado; os testes partem de 50 unidades de cada item.
            db().execute('UPDATE estoque SET quantidade=50')
            db().commit()
        self.client = app.test_client()
    def tearDown(self):
        self.tmp.cleanup()
    def post(self,url,data=None):
        self.client.get('/login')
        with self.client.session_transaction() as s: token=s['csrf']
        return self.client.post(url,data={**(data or {}),'csrf':token},follow_redirects=True)
    def register(self,renda='1000',cpf='11111111111'):
        return self.post('/cadastro',dict(nome='Pessoa Teste',cpf=cpf,telefone='84999999999',senha='Senha123!',moradores='4',criancas='1',renda=renda,ponto=PONTOS[0],consentimento='on',
            cep='59030350',logradouro='Rua Teste',numero='10',bairro='Centro',cidade='Natal',estado='RN'))
    def test_basket_hygiene_once_and_permissions(self):
        self.assertEqual(self.register().status_code,200)
        for url in ['/painel','/cesta','/pontos','/estoque','/movimentar/pedido-roupas']:
            self.assertEqual(self.client.get(url).status_code,200,url)
        self.assertEqual(self.client.get('/cadastros').status_code,403)
        self.assertEqual(self.client.get('/movimentar/alimentos').status_code,403)
        response=self.post('/cesta',{'tipo':'Emergencial','q_0':'1','q_1':'1','q_2':'1'})
        self.assertIn('Registro realizado'.encode(),response.data)
        with app.app_context():
            r=db().execute('SELECT * FROM movimentos').fetchone()
            self.assertEqual(len(json.loads(r['itens'])),8)
            self.assertEqual(db().execute("SELECT quantidade FROM estoque WHERE ponto=? AND produto='Sabonete'",(PONTOS[0],)).fetchone()[0],49)
        self.post('/cesta',{'tipo':'Emergencial','q_0':'1','q_1':'1','q_2':'1'})
        with app.app_context(): self.assertEqual(db().execute('SELECT count(*) FROM movimentos').fetchone()[0],1)
    def test_insufficient_stock_rolls_back(self):
        self.register()
        with app.app_context():
            db().execute("UPDATE estoque SET quantidade=0 WHERE produto='Óleo'")
            db().commit()
        self.post('/cesta',{'tipo':'Emergencial','q_0':'1','q_1':'1','q_2':'1'})
        with app.app_context():
            self.assertEqual(db().execute('SELECT count(*) FROM movimentos').fetchone()[0],0)
            self.assertEqual(db().execute("SELECT quantidade FROM estoque WHERE produto='Arroz' AND ponto=?",(PONTOS[0],)).fetchone()[0],50)
    def test_limits_and_clothing_independent(self):
        self.register()
        self.post('/movimentar/pedido-roupas',{'q_0':'2'})
        self.assertEqual(self.client.get('/cesta').status_code,200)
        self.post('/cesta',{'tipo':'Emergencial','q_0':'23','q_1':'1','q_2':'1'})
        with app.app_context(): self.assertEqual(db().execute("SELECT count(*) FROM movimentos WHERE tipo='Cesta'").fetchone()[0],0)
        self.post('/cesta',{'tipo':'Emergencial','q_0':'1','q_1':'1','q_2':'1'})
        with app.app_context(): self.assertEqual(db().execute('SELECT count(*) FROM movimentos').fetchone()[0],2)
    def test_donations_money_and_record_ownership(self):
        self.register('3200')
        for mode in ['alimentos','roupas','dinheiro']:
            self.assertEqual(self.client.get('/movimentar/'+mode).status_code,200)
        self.assertEqual(self.client.get('/cesta').status_code,403)
        self.post('/movimentar/alimentos',{'q_0':'3','senha':'errada','ponto':PONTOS[0]})
        with app.app_context(): self.assertEqual(db().execute('SELECT count(*) FROM movimentos').fetchone()[0],0)
        self.post('/movimentar/alimentos',{'q_0':'3','senha':'Senha123!','ponto':PONTOS[0]})
        self.post('/movimentar/roupas',{'q_0':'2','senha':'Senha123!','ponto':PONTOS[0]})
        # Pix exige chave configurada no servidor; sem redirecionar, para não depender do pacote qrcode.
        env={'PIX_CHAVE':'chave-teste@example.com','PIX_RECEBEDOR':'Rede Solidariza'}
        with mock.patch.dict(os.environ,env):
            self.client.get('/login')
            with self.client.session_transaction() as s: token=s['csrf']
            for valor in ('12.34','NaN'):
                self.client.post('/movimentar/dinheiro',data={'valor':valor,'senha':'Senha123!','ponto':PONTOS[0],'csrf':token})
        with app.app_context():
            self.assertEqual(db().execute('SELECT sum(valor) FROM movimentos').fetchone()[0],1234)
            # Doações de itens ficam pendentes: o estoque só sobe quando o administrador confirma a entrega.
            self.assertEqual(db().execute("SELECT count(*) FROM entregas WHERE status='Pendente'").fetchone()[0],2)
            self.assertEqual(db().execute("SELECT quantidade FROM estoque WHERE produto='Arroz' AND ponto=?",(PONTOS[0],)).fetchone()[0],50)
        self.post('/sair')
        self.register(cpf='22222222222')
        self.assertEqual(self.client.get('/comprovante/1').status_code,404)
    def test_auth_csrf_admin_and_persistence(self):
        self.assertEqual(self.client.get('/painel').status_code,302)
        self.client.get('/login')
        self.assertEqual(self.client.post('/cadastro',data={}).status_code,400)
        self.register()
        self.post('/sair')
        self.post('/login',{'cpf':'11111111111','senha':'Senha123!'})
        self.assertEqual(self.client.get('/painel').status_code,200)
        with app.app_context():
            db().execute('UPDATE usuarios SET admin=1')
            # Administrador só acessa Cadastros se estiver vinculado a uma unidade.
            db().execute("INSERT OR REPLACE INTO administradores_pontos SELECT id,? FROM usuarios WHERE cpf='11111111111'",(PONTOS[0],))
            db().commit()
            init_db()
            # init_db cria os administradores das unidades (cpf interno "ADMIN…"); a conta de teste não é duplicada.
            self.assertEqual(db().execute("SELECT count(*) FROM usuarios WHERE cpf NOT LIKE 'ADMIN%'").fetchone()[0],1)
        self.assertEqual(self.client.get('/cadastros').status_code,200)
        self.assertEqual(self.client.get('/estoque?ponto=Inexistente').status_code,400)

if __name__=='__main__': unittest.main()

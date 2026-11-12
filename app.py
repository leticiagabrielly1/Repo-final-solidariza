import os
import json
import time
import secrets
import sqlite3
from collections import deque
from pathlib import Path
from functools import wraps
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from math import radians, sin, cos, asin, sqrt
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, abort
from werkzeug.routing import BuildError
from werkzeug.security import generate_password_hash, check_password_hash
import rute

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
(ROOT / 'instance').mkdir(exist_ok=True)
key_file = ROOT / 'instance' / 'secret.key'
if not key_file.exists():
    try:
        with key_file.open('x') as f:
            f.write(secrets.token_hex(32))
        key_file.chmod(0o600)
    except FileExistsError:
        pass
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or key_file.read_text(),
                  DATABASE=str(ROOT / 'instance' / 'rede.db'), SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=1024 * 1024)
# Configure as unidades autorizadas no arquivo senacs.json. Endereços e coordenadas precisam ser confirmados.
SENACS_FILE = ROOT / 'senacs.json'
if not SENACS_FILE.exists():
    SENACS_FILE.write_text(json.dumps([{'nome':'Senac RN - Alecrim','endereco':'Endereço a confirmar com a unidade','latitude':None,'longitude':None}, {'nome':'Senac RN - Zona Norte','endereco':'Endereço a confirmar com a unidade','latitude':None,'longitude':None}, {'nome':'Senac RN - Centro','endereco':'Endereço a confirmar com a unidade','latitude':None,'longitude':None}], ensure_ascii=False,indent=2), encoding='utf8')
UNIDADES = json.loads(SENACS_FILE.read_text(encoding='utf8'))
if not UNIDADES:
    UNIDADES = [{'nome':'Senac RN - Alecrim','estado':'RN','endereco':'Endereço pendente de confirmação','latitude':None,'longitude':None}, {'nome':'Senac RN - Zona Norte','estado':'RN','endereco':'Endereço pendente de confirmação','latitude':None,'longitude':None}, {'nome':'Senac RN - Centro','estado':'RN','endereco':'Endereço pendente de confirmação','latitude':None,'longitude':None}]
    SENACS_FILE.write_text(json.dumps(UNIDADES,ensure_ascii=False,indent=2),encoding='utf8')
for unidade in UNIDADES:
    unidade.setdefault('estado', 'RN' if ' RN ' in unidade['nome'] else '')
ESTADOS = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']
PONTOS = [x['nome'] for x in UNIDADES]
ALIMENTOS = ['Arroz', 'Feijão', 'Óleo', 'Açúcar', 'Macarrão', 'Café', 'Leite', 'Farinha', 'Sal', 'Biscoito', 'Milho', 'Ervilha', 'Molho', 'Aveia', 'Fubá', 'Sardinha', 'Atum', 'Achocolatado', 'Macarrão instantâneo', 'Canjica']
HIGIENE = ['Sabonete', 'Pasta de dente', 'Papel higiênico', 'Shampoo', 'Detergente']
ROUPAS = ['Camisa', 'Calça', 'Sapato']
PRODUTOS = ALIMENTOS + HIGIENE
TIPOS = {'Infantil': (20, ['Leite', 'Achocolatado', 'Biscoito']), 'Emergencial': (18, ['Arroz', 'Feijão', 'Óleo']), 'Nutricional': (15, ['Arroz', 'Feijão', 'Aveia', 'Leite'])}
ICONES = {'Arroz':'🍚','Feijão':'🫘','Óleo':'🫙','Açúcar':'🥣','Macarrão':'🍝','Café':'☕','Leite':'🥛','Farinha':'🌾','Sal':'🧂','Biscoito':'🍪','Milho':'🌽','Ervilha':'🫛','Molho':'🥫','Aveia':'🌾','Fubá':'🌽','Sardinha':'🐟','Atum':'🐟','Achocolatado':'🍫','Macarrão instantâneo':'🍜','Canjica':'🥣','Sabonete':'🧼','Pasta de dente':'🪥','Papel higiênico':'🧻','Shampoo':'🧴','Detergente':'🫧','Camisa':'👕','Calça':'👖','Sapato':'👟'}

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'], timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(error):
    connection = g.pop('db', None)
    if connection is not None:
        connection.close()

def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, nome TEXT NOT NULL, cpf TEXT UNIQUE NOT NULL, telefone TEXT NOT NULL, senha TEXT NOT NULL, moradores INTEGER NOT NULL, criancas INTEGER NOT NULL, renda INTEGER NOT NULL, perfil TEXT NOT NULL, higiene INTEGER NOT NULL, codigo TEXT UNIQUE NOT NULL, ponto TEXT NOT NULL, admin INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS estoque(ponto TEXT NOT NULL, produto TEXT NOT NULL, quantidade INTEGER NOT NULL CHECK(quantidade>=0), PRIMARY KEY(ponto,produto));
    CREATE TABLE IF NOT EXISTS movimentos(id INTEGER PRIMARY KEY, usuario INTEGER NOT NULL REFERENCES usuarios(id), tipo TEXT NOT NULL, ponto TEXT NOT NULL, itens TEXT NOT NULL DEFAULT '{}', valor INTEGER NOT NULL DEFAULT 0, codigo TEXT UNIQUE NOT NULL, criado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE UNIQUE INDEX IF NOT EXISTS cesta_unica ON movimentos(usuario) WHERE tipo='Cesta';
    ''')
    c.executescript('''
    CREATE TABLE IF NOT EXISTS entregas(movimento_id INTEGER PRIMARY KEY REFERENCES movimentos(id), prazo TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pendente', confirmado_em TEXT, confirmado_por INTEGER REFERENCES usuarios(id));
    CREATE TABLE IF NOT EXISTS administradores_pontos(usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id), ponto TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS pix_cobrancas(movimento_id INTEGER PRIMARY KEY REFERENCES movimentos(id), expira_em TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Aguardando pagamento');
    ''')
    c.execute('''CREATE TABLE IF NOT EXISTS metas_gestao (id INTEGER PRIMARY KEY, ponto TEXT NOT NULL, titulo TEXT NOT NULL, tipo TEXT NOT NULL CHECK(tipo IN ('valor','doacoes','desperdicio')), alvo INTEGER NOT NULL CHECK(alvo>0), mes TEXT NOT NULL, criado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS desperdicio_registros (id INTEGER PRIMARY KEY, ponto TEXT NOT NULL, mes TEXT NOT NULL, quantidade INTEGER NOT NULL CHECK(quantidade>=0), criado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS metas_financeiras (id INTEGER PRIMARY KEY, ponto TEXT NOT NULL, titulo TEXT NOT NULL, valor_centavos INTEGER NOT NULL CHECK(valor_centavos>0), criado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS unidades_admin (
        ponto TEXT PRIMARY KEY, cep TEXT UNIQUE NOT NULL,
        usuario_id INTEGER UNIQUE NOT NULL REFERENCES usuarios(id),
        senha_hash TEXT NOT NULL, trocar_senha INTEGER NOT NULL DEFAULT 1
    )''')
    colunas = {r['name'] for r in c.execute('PRAGMA table_info(usuarios)')}
    for coluna in ('cep','logradouro','numero','complemento','bairro','cidade','estado'):
        if coluna not in colunas:
            c.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} TEXT NOT NULL DEFAULT ''")
    quantidades = [(20,15,10),(10,8,5),(12,10,7),(18,12,9),(14,11,6)]
    for i, ponto in enumerate(PONTOS):
        for produto in PRODUTOS + ROUPAS:
            quantidade = 50
            c.execute('INSERT OR IGNORE INTO estoque VALUES(?,?,?)', (ponto,produto,quantidade))
    # Corrige bancos distribuídos com estoque inteiramente vazio por unidade.
    # Só inicializa unidades sem qualquer movimentação de estoque e com todos os itens zerados.
    # Nunca repõe automaticamente estoques que já tiveram operações.
    for ponto in PONTOS:
        dados = c.execute('SELECT COUNT(*) total, COALESCE(SUM(quantidade),0) soma FROM estoque WHERE ponto=?', (ponto,)).fetchone()
        operacoes = c.execute("SELECT COUNT(*) FROM movimentos WHERE ponto=? AND tipo!='Registro de valor'", (ponto,)).fetchone()[0]
        if dados['total'] and dados['soma'] == 0 and operacoes == 0:
            c.execute('UPDATE estoque SET quantidade=50 WHERE ponto=?', (ponto,))
    c.commit()
    # Inicialização única de estoque em bancos anteriores; não repõe itens depois.
    marco_estoque = ROOT / 'instance' / '.estoque_inicial_50_v1'
    if not marco_estoque.exists():
        c.execute('UPDATE estoque SET quantidade=50 WHERE quantidade<50')
        c.commit()
        marco_estoque.write_text('Estoque inicial aplicado uma única vez.\n', encoding='utf-8')
    # Acessos iniciais fixos por CEP; aplicados uma única vez também em bancos antigos.
    acessos = {
        '59030350': 'Alecrim@2026',
        '59110185': 'ZonaNorte@2026',
        '59025030': 'Centro@2026',
    }
    marco = ROOT / 'instance' / '.admins_fixos_v1'
    for unidade in UNIDADES:
        cep = ''.join(ch for ch in str(unidade.get('cep', '')) if ch.isdigit())
        if cep not in acessos:
            continue
        ponto = unidade['nome']
        atual = c.execute('SELECT usuario_id, trocar_senha FROM unidades_admin WHERE ponto=? OR cep=?', (ponto, cep)).fetchone()
        if atual and marco.exists():
            continue
        if atual:
            usuario_id = atual['usuario_id']
            c.execute('UPDATE usuarios SET admin=1 WHERE id=?', (usuario_id,))
            c.execute('UPDATE unidades_admin SET ponto=?, cep=?, senha_hash=?, trocar_senha=1 WHERE usuario_id=?',
                      (ponto, cep, generate_password_hash(acessos[cep]), usuario_id))
        else:
            # Identificador interno reservado, não corresponde a CPF de pessoa real.
            cpf_interno = 'ADMIN' + cep
            usuario = c.execute('SELECT id FROM usuarios WHERE cpf=?', (cpf_interno,)).fetchone()
            if usuario:
                usuario_id = usuario['id']
            else:
                cur = c.execute("""INSERT INTO usuarios
                    (nome,cpf,telefone,senha,moradores,criancas,renda,perfil,higiene,codigo,ponto,admin)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,1)""",
                    ('Administrador ' + ponto, cpf_interno, '', generate_password_hash(secrets.token_urlsafe(24)),
                     0,0,0,'Administrador',0,'ADM-' + cep,ponto))
                usuario_id = cur.lastrowid
            c.execute('INSERT INTO unidades_admin(ponto,cep,usuario_id,senha_hash,trocar_senha) VALUES(?,?,?,?,1)',
                      (ponto,cep,usuario_id,generate_password_hash(acessos[cep])))
        c.execute('INSERT OR REPLACE INTO administradores_pontos(usuario_id,ponto) VALUES(?,?)', (usuario_id,ponto))
    c.commit()
    if not marco.exists():
        marco.write_text('Credenciais iniciais configuradas. Alterações futuras de senha são preservadas.\n', encoding='utf-8')

def codigo(prefix):
    return prefix + '-' + secrets.token_hex(5).upper()

def dinheiro(value):
    try:
        n = Decimal(str(value).replace(',', '.'))
        if not n.is_finite() or n < 0 or n > 100000000 or n.as_tuple().exponent < -2:
            raise ValueError
        return int(n * 100)
    except (InvalidOperation, ValueError):
        raise ValueError('Informe um valor válido, com até duas casas decimais.')

@app.template_filter('brl')
def brl(value):
    return ('R$ ' + f'{value / 100:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')

@app.before_request
def prepare():
    g.user = db().execute('SELECT * FROM usuarios WHERE id=?', (session.get('uid'),)).fetchone()
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(32)
    # Formulários enviam o token no campo "csrf"; o chat da Rute (JSON) o envia no cabeçalho X-CSRF-Token.
    token = request.form.get('csrf', '') or request.headers.get('X-CSRF-Token', '')
    if request.method == 'POST' and not secrets.compare_digest(session['csrf'], token):
        abort(400, 'Sua sessão expirou. Recarregue a página e tente novamente.')

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped

@app.context_processor
def context():
    return dict(user=g.user, pontos=PONTOS, unidades=UNIDADES, estados=ESTADOS, icones=ICONES, tipos=TIPOS,
                rute_ui=rute.config_ui(g.user))

@app.route('/')
def home():
    return redirect(url_for('painel' if g.user else 'login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        cpf = ''.join(x for x in request.form.get('cpf','') if x.isdigit())
        u = db().execute('SELECT * FROM usuarios WHERE cpf=?', (cpf,)).fetchone()
        if u and check_password_hash(u['senha'], request.form.get('senha','')):
            session.clear()
            session['uid'] = u['id']
            return redirect(url_for('admin_painel' if u['admin'] else 'painel'))
        flash('CPF ou senha incorretos.', 'error')
    return render_template('auth.html', title='Bem-vindo à Rede Solidariza', cadastro=False)

def cep_limpo(valor):
    return ''.join(c for c in valor if c.isdigit())

@app.route('/login-admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        cep = cep_limpo(request.form.get('cep', ''))
        senha = request.form.get('senha', '')
        registro = db().execute('SELECT * FROM unidades_admin WHERE cep=?', (cep,)).fetchone()
        if registro and check_password_hash(registro['senha_hash'], senha):
            session.clear()
            session['uid'] = registro['usuario_id']
            session['csrf'] = secrets.token_hex(32)
            return redirect(url_for('admin_painel'))
        flash('CEP ou senha incorretos.', 'error')
    return render_template('login_admin.html', title='Acesso administrativo')

@app.route('/admin/trocar-senha', methods=['GET','POST'])
@login_required
def trocar_senha_admin():
    registro = db().execute('SELECT * FROM unidades_admin WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not registro: abort(403)
    if request.method == 'POST':
        atual = request.form.get('atual','')
        nova = request.form.get('nova','')
        if not check_password_hash(registro['senha_hash'],atual):
            flash('Senha atual incorreta.', 'error')
        elif len(nova) < 12 or nova == registro['cep']:
            flash('Crie uma senha diferente do CEP com pelo menos 12 caracteres.', 'error')
        else:
            with db():
                db().execute('UPDATE unidades_admin SET senha_hash=?,trocar_senha=0 WHERE usuario_id=?',
                             (generate_password_hash(nova),g.user['id']))
            flash('Senha atualizada.', 'success')
            return redirect(url_for('admin_painel'))
    return render_template('trocar_senha_admin.html',title='Alterar senha administrativa')

@app.route('/configurar-primeiro-admin', methods=['GET', 'POST'])
def configurar_primeiro_admin():
    return redirect(url_for('login_admin'))

@app.route('/admin/vincular', methods=['GET','POST'])
@login_required
def vincular_admin():
    if not g.user['admin']: abort(403)
    # O primeiro administrador é o gestor das vinculações, e somente ele pode criar novos acessos.
    primeiro = db().execute('SELECT usuario_id FROM unidades_admin ORDER BY rowid LIMIT 1').fetchone()
    if not primeiro or primeiro['usuario_id'] != g.user['id']: abort(403)
    if request.method == 'POST':
        cpf = cep_limpo(request.form.get('cpf',''))
        cep = cep_limpo(request.form.get('cep',''))
        ponto = request.form.get('ponto','')
        usuario = db().execute('SELECT id FROM usuarios WHERE cpf=?',(cpf,)).fetchone()
        if not usuario or ponto not in PONTOS or len(cep) != 8:
            flash('Verifique o usuário cadastrado, o CEP e a unidade.', 'error')
        else:
            try:
                with db():
                    db().execute('UPDATE usuarios SET admin=1 WHERE id=?',(usuario['id'],))
                    db().execute('INSERT INTO administradores_pontos(usuario_id,ponto) VALUES(?,?)',(usuario['id'],ponto))
                    db().execute('INSERT INTO unidades_admin(ponto,cep,usuario_id,senha_hash) VALUES(?,?,?,?)',
                                 (ponto,cep,usuario['id'],generate_password_hash(cep)))
                flash('Administrador vinculado. Senha inicial igual ao CEP; alteração obrigatória.', 'success')
            except sqlite3.IntegrityError:
                flash('Conta, unidade ou CEP já vinculados.', 'error')
    vinculados = db().execute('SELECT ponto,cep FROM unidades_admin ORDER BY ponto').fetchall()
    return render_template('vincular_admin.html',title='Vincular administradores',vinculados=vinculados)

@app.route('/admin/unidades', methods=['GET', 'POST'])
@login_required
def administrar_unidades():
    if not g.user['admin']:
        abort(403)
    primeiro = db().execute('SELECT usuario_id FROM unidades_admin ORDER BY rowid LIMIT 1').fetchone()
    gestor = bool(primeiro and primeiro['usuario_id'] == g.user['id'])
    if request.method == 'POST' and not gestor: abort(403)
    if request.method == 'POST':
        nome = request.form.get('nome','').strip()
        estado = request.form.get('estado','').strip().upper()
        endereco = request.form.get('endereco','').strip()
        cep = cep_limpo(request.form.get('cep',''))
        if not (3 <= len(nome) <= 100 and estado in ESTADOS and len(endereco) >= 8 and len(cep) == 8):
            flash('Preencha nome, UF, endereço e CEP real da unidade.', 'error')
        elif nome in PONTOS or any(u.get('cep') == cep for u in UNIDADES):
            flash('Unidade ou CEP já cadastrado.', 'error')
        else:
            unidade = {'nome':nome,'estado':estado,'endereco':endereco,'cep':cep,'latitude':None,'longitude':None}
            UNIDADES.append(unidade)
            PONTOS.append(nome)
            try:
                SENACS_FILE.write_text(json.dumps(UNIDADES, ensure_ascii=False, indent=2),encoding='utf8')
                with db():
                    for produto in PRODUTOS + ROUPAS:
                        db().execute('INSERT OR IGNORE INTO estoque(ponto,produto,quantidade) VALUES(?,?,0)',(nome,produto))
                flash('Unidade cadastrada. Vincule o responsável em Gerenciar administradores.', 'success')
            except Exception:
                UNIDADES.remove(unidade)
                PONTOS.remove(nome)
                flash('Não foi possível salvar a unidade.', 'error')
        return redirect(url_for('administrar_unidades'))
    return render_template('administrar_unidades.html', title='Unidades Senac', gestor=gestor)

@app.route('/cadastro', methods=['GET','POST'])
def cadastro():
    if request.method == 'POST':
        try:
            nome = request.form.get('nome','').strip()
            cpf = ''.join(x for x in request.form.get('cpf','') if x.isdigit())
            telefone = ''.join(x for x in request.form.get('telefone','') if x.isdigit())
            senha = request.form.get('senha','')
            moradores = int(request.form.get('moradores','0'))
            criancas = int(request.form.get('criancas','0'))
            renda = dinheiro(request.form.get('renda',''))
            ponto = request.form.get('ponto')
            cep = ''.join(x for x in request.form.get('cep','') if x.isdigit())
            logradouro = request.form.get('logradouro','').strip()
            numero = request.form.get('numero','').strip()
            complemento = request.form.get('complemento','').strip()
            bairro = request.form.get('bairro','').strip()
            cidade = request.form.get('cidade','').strip()
            estado = request.form.get('estado','').strip().upper()
            if not 2 <= len(nome) <= 100 or len(cpf) != 11 or len(telefone) not in (10,11):
                raise ValueError('Confira nome, CPF (11 dígitos) e telefone com DDD.')
            if not 8 <= len(senha) <= 128:
                raise ValueError('A senha deve ter de 8 a 128 caracteres.')
            if not 1 <= moradores <= 100 or not 0 <= criancas <= moradores:
                raise ValueError('Confira a quantidade de moradores e crianças.')
            if ponto not in PONTOS or request.form.get('consentimento') != 'on':
                raise ValueError('Escolha um ponto e confirme o consentimento.')
            if len(cep) != 8 or not all([logradouro,numero,bairro,cidade]) or len(estado) != 2:
                raise ValueError('Preencha o endereço completo, incluindo CEP e UF.')
            if any(len(x)>120 for x in (logradouro,numero,complemento,bairro,cidade)):
                raise ValueError('Endereço muito longo.')
            perfil = 'Doador' if renda >= 80000 * moradores else 'Beneficiário'
            with db():
                cur = db().execute('INSERT INTO usuarios(nome,cpf,telefone,senha,moradores,criancas,renda,perfil,higiene,codigo,ponto,cep,logradouro,numero,complemento,bairro,cidade,estado) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (nome,cpf,telefone,generate_password_hash(senha),moradores,criancas,renda,perfil,int(renda <= 30000 * moradores),codigo('DOA' if perfil=='Doador' else 'REC'),ponto,cep,logradouro,numero,complemento,bairro,cidade,estado))
            session.clear()
            session['uid'] = cur.lastrowid
            return redirect(url_for('resultado'))
        except (ValueError, sqlite3.IntegrityError) as e:
            flash(str(e) if isinstance(e,ValueError) else 'Não foi possível cadastrar. Confira os dados ou tente entrar.', 'error')
    return render_template('auth.html', title='Vamos começar?', cadastro=True)

@app.route('/resultado')
@login_required
def resultado():
    return render_template('resultado.html', title='Resultado do cadastro')

@app.route('/painel')
@login_required
def painel():
    if g.user['admin']:
        return redirect(url_for('admin_painel'))
    registros = db().execute('SELECT * FROM movimentos WHERE usuario=? ORDER BY id DESC', (g.user['id'],)).fetchall()
    cesta = next((r for r in registros if r['tipo']=='Cesta'), None)
    return render_template('painel.html', title='Meu painel', registros=registros, cesta=cesta,
                           itens=json.loads(cesta['itens']) if cesta else {}, total=sum(r['valor'] for r in registros))

def estoque_atual(ponto):
    return {r['produto']:r['quantidade'] for r in db().execute('SELECT * FROM estoque WHERE ponto=?',(ponto,))}

def registrar(tipo, ponto, itens, direction, valor=0):
    c = db()
    try:
        c.execute('BEGIN IMMEDIATE')
        for produto, qtd in itens.items():
            cur = c.execute('UPDATE estoque SET quantidade=quantidade+? WHERE ponto=? AND produto=? AND quantidade+?>=0', (direction*qtd,ponto,produto,direction*qtd))
            if cur.rowcount != 1:
                raise ValueError(f'Estoque insuficiente de {produto}. Nenhum item foi registrado.')
        cur = c.execute('INSERT INTO movimentos(usuario,tipo,ponto,itens,valor,codigo) VALUES(?,?,?,?,?,?)', (g.user['id'],tipo,ponto,json.dumps(itens,ensure_ascii=False),valor,codigo('RS')))
        c.commit()
        return cur.lastrowid
    except Exception:
        c.rollback()
        raise

@app.route('/cesta', methods=['GET','POST'])
@login_required
def cesta():
    if g.user['perfil'] != 'Beneficiário':
        abort(403)
    if db().execute("SELECT id FROM movimentos WHERE usuario=? AND tipo='Cesta'",(g.user['id'],)).fetchone():
        flash('Sua cesta já está registrada. Consulte o código no painel.', 'info')
        return redirect(url_for('painel'))
    tipo = request.values.get('tipo','Emergencial')
    if tipo not in TIPOS:
        abort(400)
    limite, obrigatorios = TIPOS[tipo]
    limite += 5 if g.user['criancas'] else 0
    extras = HIGIENE if g.user['higiene'] else []
    if request.method == 'POST':
        try:
            itens = {}
            for i, p in enumerate(PRODUTOS):
                n = int(request.form.get(f'q_{i}','0'))
                if n < 0 or n > limite:
                    raise ValueError('Quantidade fora do limite.')
                if n:
                    itens[p] = n
            for p in obrigatorios:
                if itens.get(p,0) < 1:
                    raise ValueError('Mantenha ao menos uma unidade de cada item obrigatório.')
            if sum(itens.values()) > limite:
                raise ValueError('O limite da cesta foi excedido.')
            for p in extras:
                itens[p] = itens.get(p,0) + 1
            mid = registrar('Cesta',g.user['ponto'],itens,-1)
            return redirect(url_for('comprovante',mid=mid))
        except (ValueError,sqlite3.IntegrityError) as e:
            flash(str(e) if isinstance(e,ValueError) else 'Esta cesta já foi registrada.', 'error')
    return render_template('cesta.html',title='Monte sua cesta',produtos=PRODUTOS, tipo=tipo,limite=limite,obrigatorios=obrigatorios,extras=extras,estoque=estoque_atual(g.user['ponto']))

@app.route('/movimentar/<modo>', methods=['GET','POST'])
@login_required
def movimentar(modo):
    opcoes = {'alimentos':('Doação de alimentos',PRODUTOS,1),'roupas':('Doação de roupas',ROUPAS,1),'pedido-roupas':('Pedido de roupas',ROUPAS,-1),'dinheiro':('Registro de valor',[],0)}
    if modo not in opcoes:
        abort(404)
    title, produtos, direction = opcoes[modo]
    if (direction >= 0 and g.user['perfil'] != 'Doador') or (direction < 0 and g.user['perfil'] != 'Beneficiário'):
        abort(403)
    ponto = request.form.get('ponto',g.user['ponto']) if direction >= 0 else g.user['ponto']
    if request.method == 'POST':
        try:
            if ponto not in PONTOS:
                raise ValueError('Escolha um ponto válido.')
            if direction >= 0 and not check_password_hash(g.user['senha'],request.form.get('senha','')):
                raise ValueError('Senha incorreta. Confirme sua senha para registrar.')
            itens = {}
            for i,p in enumerate(produtos):
                n = int(request.form.get(f'q_{i}','0'))
                if not 0 <= n <= 10000:
                    raise ValueError('Use quantidades de 0 a 10.000.')
                if n:
                    itens[p] = n
            valor = dinheiro(request.form.get('valor','0')) if modo=='dinheiro' else 0
            if not itens and valor <= 0:
                raise ValueError('Adicione itens ou informe um valor positivo.')
            if modo in ('alimentos','roupas'):
                c=db()
                try:
                    c.execute('BEGIN IMMEDIATE')
                    cur=c.execute('INSERT INTO movimentos(usuario,tipo,ponto,itens,valor,codigo) VALUES(?,?,?,?,?,?)',(g.user['id'],title,ponto,json.dumps(itens,ensure_ascii=False),0,codigo('RS')))
                    mid=cur.lastrowid
                    prazo=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()
                    c.execute('INSERT INTO entregas(movimento_id,prazo) VALUES(?,?)',(mid,prazo))
                    c.commit()
                except Exception:
                    c.rollback(); raise
            elif modo=='dinheiro':
                chave='DEMO-' + secrets.token_hex(8)

                recebedor='REDE SOLIDARIZA DEMO'
                cidade=os.environ.get('PIX_CIDADE','NATAL').strip()

                payload=f'REDE SOLIDARIZA | SIMULACAO SEM VALOR FINANCEIRO | CHAVE {chave} | VALOR {valor/100:.2f}'
                c=db()
                with c:
                    cur=c.execute('INSERT INTO movimentos(usuario,tipo,ponto,itens,valor,codigo) VALUES(?,?,?,?,?,?)',(g.user['id'],title,ponto,'{}',valor,codigo('RS')))
                    mid=cur.lastrowid
                    c.execute('INSERT INTO pix_cobrancas(movimento_id,expira_em,payload) VALUES(?,?,?)',(mid,(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),payload))
            else:
                mid = registrar(title,ponto,itens,direction,valor)
            return redirect(url_for('comprovante',mid=mid))
        except ValueError as e:
            flash(str(e),'error')
    return render_template('movimentar.html',title=title,modo=modo,produtos=produtos,direction=direction,estoque=estoque_atual(g.user['ponto']))

@app.route('/comprovante/<int:mid>')
@login_required
def comprovante(mid):
    r = db().execute('SELECT * FROM movimentos WHERE id=? AND usuario=?',(mid,g.user['id'])).fetchone()
    if not r:
        abort(404)
    entrega=db().execute('SELECT * FROM entregas WHERE movimento_id=?',(mid,)).fetchone()
    pix=db().execute('SELECT * FROM pix_cobrancas WHERE movimento_id=?',(mid,)).fetchone()
    if pix and datetime.fromisoformat(pix['expira_em']) <= datetime.now(timezone.utc) and pix['status']=='Aguardando pagamento':
        with db(): db().execute("UPDATE pix_cobrancas SET status='Expirado' WHERE movimento_id=?",(mid,))
        pix=db().execute('SELECT * FROM pix_cobrancas WHERE movimento_id=?',(mid,)).fetchone()
    qr=None
    if pix and pix['status']=='Aguardando pagamento':
        import qrcode, io, base64
        out=io.BytesIO(); qrcode.make(pix['payload']).save(out,format='PNG'); qr=base64.b64encode(out.getvalue()).decode()
    return render_template('comprovante.html',title='Registro concluído',r=r,itens=json.loads(r['itens']),entrega=entrega,pix=pix,qr=qr)

@app.route('/pontos',methods=['GET','POST'])
@login_required
def pontos():
    if request.method == 'POST':
        p = request.form.get('ponto')
        if p not in PONTOS:
            abort(400)
        with db():
            db().execute('UPDATE usuarios SET ponto=? WHERE id=?',(p,g.user['id']))
        flash('Ponto atualizado para os próximos registros. Registros anteriores mantêm seu destino.','success')
        return redirect(url_for('pontos'))
    return render_template('pontos.html',title='Pontos de coleta', estado_selecionado=request.args.get('estado',''))

@app.route('/estoque')
@login_required
def estoque():
    if g.user and g.user['perfil']=='Beneficiário' and not g.user['admin']: abort(403)
    p = request.args.get('ponto',g.user['ponto'])
    if p not in PONTOS:
        abort(400)
    return render_template('estoque.html',title='Estoque por ponto',ponto=p,estoque=estoque_atual(p))

@app.route('/cadastros')
@login_required
def cadastros():
    if not g.user['admin']:
        abort(403)
    vinculo=db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not vinculo: abort(403)
    pessoas = db().execute('SELECT nome,perfil,moradores,criancas,ponto,codigo FROM usuarios WHERE ponto=? ORDER BY nome',(vinculo['ponto'],)).fetchall()
    valores = db().execute('SELECT u.nome, SUM(m.valor) AS total FROM movimentos m JOIN usuarios u ON u.id=m.usuario WHERE m.valor>0 AND m.ponto=? GROUP BY u.id ORDER BY total DESC',(vinculo['ponto'],)).fetchall()
    return render_template('cadastros.html',title='Cadastros',pessoas=pessoas,valores=valores,total=sum(r['total'] for r in valores))

@app.cli.command('tornar-admin')
def tornar_admin():
    import click
    cpf = click.prompt('CPF da conta que será administradora')
    with db():
        ponto=click.prompt('Nome exato da unidade Senac')
        if ponto not in PONTOS:
            click.echo('Unidade inválida. Consulte senacs.json.'); return
        cur = db().execute('UPDATE usuarios SET admin=1 WHERE cpf=?',(cpf,))
        usuario=db().execute('SELECT id FROM usuarios WHERE cpf=?',(cpf,)).fetchone()
        if usuario: db().execute('INSERT OR REPLACE INTO administradores_pontos VALUES(?,?)',(usuario['id'],ponto))
    click.echo('Conta atualizada.' if cur.rowcount else 'Conta não encontrada.')

def campo_pix(tag, value):
    value=str(value)
    return f'{tag}{len(value.encode("utf8")):02d}{value}'

def gerar_pix(chave, recebedor, cidade, centavos):
    # BR Code estático (EMV); a validade de 5 minutos é controlada pelo sistema,
    # NÃO pelo banco recebedor. Sem PSP, não há expiração bancária nem confirmação automática.
    conta=campo_pix('00','br.gov.bcb.pix')+campo_pix('01',chave)
    base=campo_pix('00','01')+campo_pix('26',conta)+campo_pix('52','0000')+campo_pix('53','986')
    base+=campo_pix('54',f'{centavos/100:.2f}')+campo_pix('58','BR')
    base+=campo_pix('59',recebedor[:25])+campo_pix('60',cidade[:15])
    base+=campo_pix('62',campo_pix('05','***'))+'6304'
    crc=0xFFFF
    for b in base.encode('utf8'):
        crc^=b<<8
        for _ in range(8): crc=((crc<<1)^0x1021) & 0xFFFF if crc & 0x8000 else (crc<<1)&0xFFFF
    return base+f'{crc:04X}'

@app.route('/admin')
@login_required
def admin_painel():
    if not g.user['admin']: abort(403)
    vinculo=db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not vinculo: abort(403)
    ponto=vinculo['ponto']
    resumo=db().execute("""SELECT COUNT(*) AS total,
        SUM(CASE WHEN e.status='Pendente' THEN 1 ELSE 0 END) AS pendentes,
        SUM(CASE WHEN e.status='Entregue' THEN 1 ELSE 0 END) AS entregues
        FROM entregas e JOIN movimentos m ON m.id=e.movimento_id WHERE m.ponto=?""",(ponto,)).fetchone()
    recentes=db().execute("""SELECT m.id,m.codigo,m.tipo,u.nome,e.prazo,e.status
        FROM entregas e JOIN movimentos m ON m.id=e.movimento_id
        JOIN usuarios u ON u.id=m.usuario WHERE m.ponto=?
        ORDER BY CASE WHEN e.status='Pendente' THEN 0 ELSE 1 END,m.id DESC LIMIT 12""",(ponto,)).fetchall()
    financeiro=db().execute("""SELECT COUNT(*) quantidade, COALESCE(SUM(valor),0) total FROM movimentos WHERE ponto=? AND tipo='Registro de valor'""",(ponto,)).fetchone()
    historico=db().execute("""SELECT m.criado,m.valor,u.nome,p.status FROM movimentos m JOIN usuarios u ON u.id=m.usuario LEFT JOIN pix_cobrancas p ON p.movimento_id=m.id WHERE m.ponto=? AND m.tipo='Registro de valor' ORDER BY m.id DESC LIMIT 20""",(ponto,)).fetchall()
    mensal=db().execute("""SELECT substr(criado,1,7) mes, SUM(valor) total FROM movimentos WHERE ponto=? AND tipo='Registro de valor' GROUP BY substr(criado,1,7) ORDER BY mes DESC LIMIT 12""",(ponto,)).fetchall()
    metas=db().execute('SELECT * FROM metas_financeiras WHERE ponto=? ORDER BY id DESC',(ponto,)).fetchall()
    from datetime import date
    from calendar import monthrange
    hoje=date.today()
    periodos=[]
    for offset in range(11,-1,-1):
        ano=hoje.year-(offset//12)
        mes=hoje.month-(offset%12)
        if mes<=0: mes+=12; ano-=1
        chave=f'{ano:04d}-{mes:02d}'
        row=db().execute("SELECT COUNT(*) qtd,COALESCE(SUM(valor),0) valor FROM movimentos WHERE ponto=? AND tipo='Registro de valor' AND substr(criado,1,7)=?",(ponto,chave)).fetchone()
        fisicos=db().execute("SELECT COUNT(*) qtd FROM movimentos WHERE ponto=? AND tipo!='Registro de valor' AND substr(criado,1,7)=?",(ponto,chave)).fetchone()
        perdas=db().execute('SELECT COALESCE(SUM(quantidade),0) total,COUNT(*) registros FROM desperdicio_registros WHERE ponto=? AND mes=?',(ponto,chave)).fetchone()
        periodos.append(dict(mes=chave,valor=row['valor'],doacoes=row['qtd']+fisicos['qtd'],desperdicio=perdas['total'],registros_perdas=perdas['registros']))
    atual,anterior=periodos[-1],periodos[-2]
    def variacao(a,b):
        return round((a-b)*100/b,1) if b else (0 if a==0 else None)
    comparativo={k:variacao(atual[k],anterior[k]) for k in ('valor','doacoes','desperdicio')}
    metas_gestao=[]
    for meta in db().execute('SELECT * FROM metas_gestao WHERE ponto=? ORDER BY mes DESC,id DESC',(ponto,)):
        dados=next((x for x in periodos if x['mes']==meta['mes']),None)
        if dados is None:
            row=db().execute("SELECT COUNT(*) qtd,COALESCE(SUM(valor),0) valor FROM movimentos WHERE ponto=? AND tipo='Registro de valor' AND substr(criado,1,7)=?",(ponto,meta['mes'])).fetchone()
            n=db().execute("SELECT COUNT(*) qtd FROM movimentos WHERE ponto=? AND tipo!='Registro de valor' AND substr(criado,1,7)=?",(ponto,meta['mes'])).fetchone()
            dados={'valor':row['valor'],'doacoes':row['qtd']+n['qtd']}
        if meta['tipo']=='desperdicio':
            y,m=map(int,meta['mes'].split('-')); mes_ant=f'{y-1:04d}-12' if m==1 else f'{y:04d}-{m-1:02d}'
            ant=db().execute('SELECT COALESCE(SUM(quantidade),0) total,COUNT(*) qtd FROM desperdicio_registros WHERE ponto=? AND mes=?',(ponto,mes_ant)).fetchone()
            atu=db().execute('SELECT COALESCE(SUM(quantidade),0) total,COUNT(*) qtd FROM desperdicio_registros WHERE ponto=? AND mes=?',(ponto,meta['mes'])).fetchone()
            atingido=round(max(0,(ant['total']-atu['total'])*100/ant['total']),1) if ant['total'] and ant['qtd'] and atu['qtd'] else None
        else: atingido=dados[meta['tipo']]
        progresso=round(atingido*100/meta['alvo'],1) if atingido is not None else None
        metas_gestao.append(dict(meta=dict(meta),atingido=atingido,progresso=progresso))
    for i, periodo in enumerate(periodos):
        anterior_periodo = periodos[i-1] if i else None
        periodo['crescimento'] = (round((periodo['doacoes']-anterior_periodo['doacoes'])*100/anterior_periodo['doacoes'],1)
            if anterior_periodo and anterior_periodo['doacoes'] else None)
        periodo['reducao'] = (round((anterior_periodo['desperdicio']-periodo['desperdicio'])*100/anterior_periodo['desperdicio'],1)
            if anterior_periodo and anterior_periodo['registros_perdas'] and periodo['registros_perdas'] and anterior_periodo['desperdicio'] else None)
    # Resumo operacional por unidade: estoque, necessidades e doações físicas.
    linhas_estoque=db().execute('SELECT produto,quantidade FROM estoque WHERE ponto=? ORDER BY produto',(ponto,)).fetchall()
    qtd_roupas=sum(r['quantidade'] for r in linhas_estoque if r['produto'] in ROUPAS)
    qtd_alimentos=sum(r['quantidade'] for r in linhas_estoque if r['produto'] in ALIMENTOS)
    qtd_higiene=sum(r['quantidade'] for r in linhas_estoque if r['produto'] in HIGIENE)
    estoque_baixo=sum(1 for r in linhas_estoque if r['quantidade']<10)
    necessidades=db().execute("SELECT tipo,COUNT(*) total FROM movimentos WHERE ponto=? AND tipo='Cesta' GROUP BY tipo",(ponto,)).fetchall()
    familias=db().execute("SELECT COUNT(*) total,COALESCE(SUM(moradores),0) pessoas FROM usuarios WHERE ponto=? AND perfil='Beneficiário'",(ponto,)).fetchone()
    pedidos=db().execute("SELECT COUNT(*) total FROM movimentos WHERE ponto=? AND tipo='Cesta'",(ponto,)).fetchone()['total']
    tipos_doacoes=db().execute("SELECT tipo,COUNT(*) total FROM movimentos WHERE ponto=? AND tipo IN ('Doação de roupas','Doação de alimentos','Registro de valor') GROUP BY tipo",(ponto,)).fetchall()
    contagem_tipos={r['tipo']:r['total'] for r in tipos_doacoes}
    # Demandas: pedidos de cesta e beneficiários cadastrados; não confundir com estoque.
    panorama={'roupas':qtd_roupas,'alimentos':qtd_alimentos,'higiene':qtd_higiene,'total_estoque':sum(r['quantidade'] for r in linhas_estoque),'estoque_baixo':estoque_baixo,'familias':familias['total'],'pessoas':familias['pessoas'],'pedidos':pedidos,'doacoes_roupas':contagem_tipos.get('Doação de roupas',0),'doacoes_alimentos':contagem_tipos.get('Doação de alimentos',0),'doacoes_pix':contagem_tipos.get('Registro de valor',0)}
    itens_estoque=[{'produto':r['produto'],'quantidade':r['quantidade'],'categoria':'Roupas' if r['produto'] in ROUPAS else 'Alimentos' if r['produto'] in ALIMENTOS else 'Higiene'} for r in linhas_estoque]
    graficos_metas = [{'nome': item['meta']['titulo'], 'progresso': item['progresso']} for item in metas_gestao]
    return render_template('admin_painel.html',panorama=panorama,itens_estoque=itens_estoque,graficos_metas=graficos_metas,title='Painel do administrador',ponto=ponto,resumo=resumo,recentes=recentes,financeiro=financeiro,historico=historico,mensal=list(reversed(mensal)),metas=metas,metas_gestao=metas_gestao,periodos=periodos,comparativo=comparativo,atual=atual,anterior=anterior)


@app.route('/admin/metas',methods=['POST'])
@login_required
def adicionar_meta():
    if not g.user['admin']: abort(403)
    vinculo=db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not vinculo: abort(403)
    titulo=request.form.get('titulo','').strip()[:90]
    try: valor=dinheiro(request.form.get('valor',''))
    except ValueError: valor=0
    if not titulo or valor<=0:
        flash('Informe um título e um valor de meta válido.','error')
    else:
        with db(): db().execute('INSERT INTO metas_financeiras(ponto,titulo,valor_centavos) VALUES(?,?,?)',(vinculo['ponto'],titulo,valor))
        flash('Meta demonstrativa registrada.','success')
    return redirect(url_for('admin_painel'))

@app.route('/admin/metas/gestao',methods=['POST'])
@login_required
def criar_meta_gestao():
    if not g.user['admin']: abort(403)
    vinculo=db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not vinculo: abort(403)
    titulo=request.form.get('titulo','').strip()[:90]
    tipo=request.form.get('tipo','')
    mes=request.form.get('mes','')
    import re
    try:
        if tipo=='valor': alvo=dinheiro(request.form.get('alvo',''))
        else: alvo=int(request.form.get('alvo',''))
    except (ValueError,TypeError): alvo=0
    valido=bool(re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',mes))
    if not titulo or tipo not in ('valor','doacoes','desperdicio') or not valido or alvo<=0 or (tipo=='desperdicio' and alvo>100) or alvo>100000000000:
        flash('Confira o título, tipo, mês e valor da meta.','error')
    else:
        with db(): db().execute('INSERT INTO metas_gestao(ponto,titulo,tipo,alvo,mes) VALUES(?,?,?,?,?)',(vinculo['ponto'],titulo,tipo,alvo,mes))
        flash('Meta cadastrada para esta unidade.','success')
    return redirect(url_for('admin_painel'))

@app.route('/admin/desperdicio',methods=['POST'])
@login_required
def registrar_desperdicio():
    if not g.user['admin']: abort(403)
    vinculo=db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not vinculo: abort(403)
    import re
    mes=request.form.get('mes','')
    try: quantidade=int(request.form.get('quantidade',''))
    except (ValueError,TypeError): quantidade=-1
    if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',mes) or not 0<=quantidade<=10000000:
        flash('Informe mês e quantidade válida.','error')
    else:
        with db(): db().execute('INSERT INTO desperdicio_registros(ponto,mes,quantidade) VALUES(?,?,?)',(vinculo['ponto'],mes,quantidade))
        flash('Registro de desperdício adicionado.','success')
    return redirect(url_for('admin_painel'))

@app.route('/admin/doacoes')
@login_required
def admin_doacoes():
    if not g.user['admin']:
        abort(403)
    vinculo = db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?', (g.user['id'],)).fetchone()
    if not vinculo:
        abort(403)
    categoria = request.args.get('tipo', 'todas')
    filtros = {
        'todas': None,
        'pix': 'Registro de valor',
        'roupas': 'Doação de roupas',
        'alimentos': 'Doação de alimentos',
    }
    if categoria not in filtros:
        abort(404)
    sql = """SELECT m.id, m.codigo, m.tipo, m.itens, m.valor, m.criado,
                    u.nome, e.status AS entrega_status, e.prazo,
                    p.status AS pix_status, p.expira_em
             FROM movimentos m
             JOIN usuarios u ON u.id=m.usuario
             LEFT JOIN entregas e ON e.movimento_id=m.id
             LEFT JOIN pix_cobrancas p ON p.movimento_id=m.id
             WHERE m.ponto=? AND m.tipo IN ('Registro de valor','Doação de roupas','Doação de alimentos')"""
    parametros = [vinculo['ponto']]
    if filtros[categoria]:
        sql += ' AND m.tipo=?'
        parametros.append(filtros[categoria])
    sql += ' ORDER BY m.id DESC'
    registros = db().execute(sql, parametros).fetchall()
    return render_template('admin_doacoes.html', title='Doações da unidade',
                           ponto=vinculo['ponto'], registros=registros, categoria=categoria)

@app.route('/admin/entregas')
@login_required
def admin_entregas():
    if not g.user['admin']: abort(403)
    vinculo=db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not vinculo: abort(403)
    registros=db().execute("""SELECT m.id,m.codigo,m.tipo,m.itens,m.criado,e.prazo,e.status,u.nome
        FROM entregas e JOIN movimentos m ON m.id=e.movimento_id
        JOIN usuarios u ON u.id=m.usuario WHERE m.ponto=? ORDER BY e.status DESC,m.id DESC""",(vinculo['ponto'],)).fetchall()
    return render_template('admin_entregas.html',title='Entregas da unidade',registros=registros,ponto=vinculo['ponto'])

@app.route('/admin/entregas/<int:mid>/confirmar',methods=['POST'])
@login_required
def confirmar_entrega(mid):
    if not g.user['admin']: abort(403)
    vinculo=db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not vinculo: abort(403)
    c=db()
    try:
        c.execute('BEGIN IMMEDIATE')
        r=c.execute("""SELECT m.ponto,m.itens FROM movimentos m JOIN entregas e ON e.movimento_id=m.id
            WHERE m.id=? AND e.status='Pendente' """,(mid,)).fetchone()
        if not r or r['ponto']!=vinculo['ponto']: abort(404)
        for produto,qtd in json.loads(r['itens']).items():
            c.execute('UPDATE estoque SET quantidade=quantidade+? WHERE ponto=? AND produto=?',(qtd,r['ponto'],produto))
        c.execute("UPDATE entregas SET status='Entregue',confirmado_em=?,confirmado_por=? WHERE movimento_id=?",(datetime.now(timezone.utc).isoformat(),g.user['id'],mid))
        c.commit()
    except Exception:
        c.rollback(); raise
    flash('Entrega confirmada e estoque atualizado.','success')
    return redirect(url_for('admin_entregas'))

@app.route('/admin/estoque', methods=['GET','POST'])
@login_required
def admin_estoque():
    if not g.user['admin']: abort(403)
    vinculo=db().execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?',(g.user['id'],)).fetchone()
    if not vinculo or vinculo['ponto'] not in PONTOS: abort(403)
    ponto=vinculo['ponto']
    if request.method == 'POST':
        produto=request.form.get('produto','')
        try:
            quantidade=int(request.form.get('quantidade',''))
            if produto not in PRODUTOS + ROUPAS or not -10000 <= quantidade <= 10000 or quantidade == 0:
                raise ValueError('Produto ou quantidade inválida.')
            with db():
                cur=db().execute('UPDATE estoque SET quantidade=quantidade+? WHERE ponto=? AND produto=? AND quantidade+?>=0', (quantidade,ponto,produto,quantidade))
                if cur.rowcount != 1: raise ValueError('Estoque insuficiente para este ajuste.')
            flash('Estoque ajustado.', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        return redirect(url_for('admin_estoque'))
    return render_template('admin_estoque.html',title='Controle de estoque',ponto=ponto,estoque=estoque_atual(ponto))

@app.route('/api/pontos-proximos')
@login_required
def pontos_proximos():
    try:
        lat=float(request.args['lat']); lon=float(request.args['lon'])
        if not -90<=lat<=90 or not -180<=lon<=180: abort(400)
    except (KeyError,ValueError): abort(400)
    def distancia(x):
        a=radians(lat); b=radians(float(x['latitude'])); dl=radians(float(x['longitude'])-lon)
        h=sin((b-a)/2)**2+cos(a)*cos(b)*sin(dl/2)**2
        return 12742*asin(min(1,sqrt(h)))
    disponiveis=[dict(x,distancia_km=round(distancia(x),2)) for x in UNIDADES if x.get('latitude') is not None and x.get('longitude') is not None]
    return {'pontos':sorted(disponiveis,key=lambda x:x['distancia_km'])}

# ---------------------------------------------------------------------------
# Rute, assistente virtual (lógica de conversa em rute.py)
# ---------------------------------------------------------------------------
RUTE_MAX_MENSAGENS = 20   # por janela
RUTE_JANELA_SEGUNDOS = 60
_rute_janelas = {}

def rute_limite_excedido():
    """Limite simples em memória por IP e conta, para evitar abuso do endpoint."""
    chave = (request.remote_addr or '-', g.user['id'] if g.user else 0)
    agora = time.monotonic()
    fila = _rute_janelas.setdefault(chave, deque())
    while fila and agora - fila[0] > RUTE_JANELA_SEGUNDOS:
        fila.popleft()
    if len(fila) >= RUTE_MAX_MENSAGENS:
        return True
    fila.append(agora)
    if len(_rute_janelas) > 5000:
        for k in [k for k, v in _rute_janelas.items() if not v]:
            del _rute_janelas[k]
    return False

def rute_contexto():
    """Dados que a Rute pode usar: somente da própria conta e da própria unidade. Nunca CPF, senha, renda ou telefone."""
    perfil = rute.perfil_de(g.user)
    ctx = {'perfil': perfil, 'nome': g.user['nome'].split()[0] if g.user else '', 'tipos': TIPOS,
           'unidades': [{'nome': u['nome'], 'endereco': u.get('endereco', '')} for u in UNIDADES]}
    if not g.user:
        return ctx
    c = db()
    if perfil == 'admin':
        vinculo = c.execute('SELECT ponto FROM administradores_pontos WHERE usuario_id=?', (g.user['id'],)).fetchone()
        ponto = vinculo['ponto'] if vinculo else None
    else:
        ponto = g.user['ponto']
    ctx['ponto'] = ponto
    if ponto in PONTOS:
        estoque = estoque_atual(ponto)
        baixos = sorted(((p, estoque.get(p, 0)) for p in PRODUTOS + ROUPAS if estoque.get(p, 0) < rute.LIMIAR_ESTOQUE_BAIXO),
                        key=lambda x: x[1])
        ctx['falta'] = [{'produto': p, 'quantidade': q} for p, q in baixos]
    if perfil == 'doador':
        r = c.execute('SELECT COUNT(*) AS n, COALESCE(SUM(valor),0) AS v FROM movimentos WHERE usuario=?', (g.user['id'],)).fetchone()
        ctx.update(registros=r['n'], total_valor=r['v'])
        ctx['pendentes'] = c.execute("""SELECT COUNT(*) FROM entregas e JOIN movimentos m ON m.id=e.movimento_id
            WHERE m.usuario=? AND e.status='Pendente'""", (g.user['id'],)).fetchone()[0]
    elif perfil == 'beneficiario':
        cesta = c.execute("SELECT codigo FROM movimentos WHERE usuario=? AND tipo='Cesta'", (g.user['id'],)).fetchone()
        ctx.update(cesta_codigo=cesta['codigo'] if cesta else None, criancas=g.user['criancas'], higiene=bool(g.user['higiene']))
    elif ponto:
        r = c.execute("""SELECT COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN e.status='Pendente' THEN 1 ELSE 0 END),0) AS pendentes,
            COALESCE(SUM(CASE WHEN e.status='Entregue' THEN 1 ELSE 0 END),0) AS entregues
            FROM entregas e JOIN movimentos m ON m.id=e.movimento_id WHERE m.ponto=?""", (ponto,)).fetchone()
        ctx.update(total_entregas=r['total'], pendentes=r['pendentes'], entregues=r['entregues'])
        v = c.execute("SELECT COUNT(*) AS n, COALESCE(SUM(valor),0) AS v FROM movimentos WHERE ponto=? AND tipo='Registro de valor'", (ponto,)).fetchone()
        ctx.update(valores_qtd=v['n'], valores_total=v['v'])
        primeiro = c.execute('SELECT usuario_id FROM unidades_admin ORDER BY rowid LIMIT 1').fetchone()
        ctx['gestor'] = bool(primeiro and primeiro['usuario_id'] == g.user['id'])
    return ctx

@app.route('/rute/mensagem', methods=['POST'])
def rute_mensagem():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return {'erro': 'Mensagem inválida.'}, 400
    pergunta = str(dados.get('mensagem', '')).strip()
    if not pergunta:
        return {'erro': 'Escreva uma mensagem para a Rute.'}, 400
    if len(pergunta) > rute.LIMITE_MENSAGEM:
        return {'erro': f'Use até {rute.LIMITE_MENSAGEM} caracteres.'}, 400
    if rute_limite_excedido():
        return {'erro': 'Muitas mensagens em pouco tempo. Aguarde um instante e tente de novo.'}, 429
    historico = dados.get('historico')
    resposta = rute.responder(pergunta, rute_contexto(), historico if isinstance(historico, list) else [])
    acoes = []
    for rotulo, endpoint, args in resposta['acoes']:
        try:
            acoes.append({'rotulo': rotulo, 'url': url_for(endpoint, **args)})
        except BuildError:
            continue
    return {'resposta': resposta['resposta'], 'sugestoes': resposta['sugestoes'], 'acoes': acoes, 'origem': resposta['origem']}

@app.route('/sair',methods=['POST'])
@login_required
def sair():
    session.clear()
    return redirect(url_for('login'))

@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
def error(e):
    return render_template('erro.html',title='Não foi possível continuar',error=e),e.code

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)

/* Sofia, assistente virtual da Rede Solidariza. JavaScript puro, sem dependências. */
(() => {
  const raiz = document.getElementById('rute');
  if (!raiz) return;

  const $ = id => document.getElementById(id);
  const fab = $('rute-fab'), painel = $('rute-panel'), log = $('rute-log'), chips = $('rute-sugestoes');
  const form = $('rute-form'), entrada = $('rute-entrada'), enviar = $('rute-enviar');
  const MAX_SALVAS = 30;
  const PREFIXO = 'rute:v1:';
  const chave = PREFIXO + (raiz.dataset.chave || 'visitante');
  const reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)');
  const celular = window.matchMedia('(max-width:780px)');

  let mensagens = [];          // {papel:'usuario'|'rute', texto, acoes?}
  let sugestoesAtuais = [];
  let aguardando = false;

  // ---------- armazenamento (por aba; pode falhar em navegação privada) ----------
  function carregar() {
    try {
      const salvo = JSON.parse(sessionStorage.getItem(chave) || 'null');
      if (salvo && Array.isArray(salvo.mensagens)) {
        mensagens = salvo.mensagens.slice(-MAX_SALVAS);
        sugestoesAtuais = Array.isArray(salvo.sugestoes) ? salvo.sugestoes : [];
      }
    } catch (e) { mensagens = []; }
  }
  function salvar() {
    try { sessionStorage.setItem(chave, JSON.stringify({ mensagens: mensagens.slice(-MAX_SALVAS), sugestoes: sugestoesAtuais })); } catch (e) { /* sem armazenamento */ }
  }
  function esquecerTudo() {
    try { Object.keys(sessionStorage).filter(k => k.startsWith(PREFIXO)).forEach(k => sessionStorage.removeItem(k)); } catch (e) { /* ok */ }
  }
  // Ao sair da conta, nenhuma conversa fica para a próxima pessoa que usar este navegador.
  document.querySelectorAll('form[action$="/sair"]').forEach(f => f.addEventListener('submit', esquecerTudo));

  // ---------- renderização segura (sempre textContent, nunca innerHTML) ----------
  function inline(pai, texto) {
    texto.split(/(\*\*[^*]+\*\*)/g).forEach(parte => {
      if (/^\*\*[^*]+\*\*$/.test(parte)) {
        const b = document.createElement('strong');
        b.textContent = parte.slice(2, -2);
        pai.append(b);
      } else if (parte) {
        pai.append(document.createTextNode(parte));
      }
    });
  }
  function corpo(el, texto) {
    let lista = null;
    texto.split('\n').forEach(linha => {
      if (/^\s*- /.test(linha)) {
        if (!lista) { lista = document.createElement('ul'); el.append(lista); }
        const li = document.createElement('li');
        inline(li, linha.replace(/^\s*- /, ''));
        lista.append(li);
      } else {
        lista = null;
        if (!linha.trim()) return;
        const p = document.createElement('p');
        inline(p, linha);
        el.append(p);
      }
    });
  }
  function bolha(msg) {
    const li = document.createElement('div');
    li.className = 'rute-msg rute-msg--' + (msg.papel === 'usuario' ? 'eu' : 'rute');
    const balao = document.createElement('div');
    balao.className = 'rute-balao';
    corpo(balao, msg.texto);
    li.append(balao);
    if (msg.acoes && msg.acoes.length) {
      const grupo = document.createElement('div');
      grupo.className = 'rute-acoes';
      msg.acoes.forEach(a => {
        // Só links relativos do próprio site.
        if (typeof a.url !== 'string' || !a.url.startsWith('/')) return;
        const link = document.createElement('a');
        link.href = a.url;
        link.textContent = a.rotulo + ' →';
        grupo.append(link);
      });
      if (grupo.children.length) li.append(grupo);
    }
    return li;
  }
  function rolar() { log.scrollTop = log.scrollHeight; }
  function adicionar(msg, animar = true) {
    const el = bolha(msg);
    if (!animar) el.classList.add('rute-msg--sem-animacao');
    log.append(el);
    rolar();
  }
  function desenharSugestoes() {
    chips.replaceChildren();
    sugestoesAtuais.forEach(texto => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'rute-chip';
      b.textContent = texto;
      b.addEventListener('click', () => perguntar(texto));
      chips.append(b);
    });
    chips.hidden = sugestoesAtuais.length === 0;
    // As sugestões mudam a altura da conversa: rolar de novo mantém o fim da mensagem visível.
    rolar();
  }
  function digitando(mostrar) {
    const antigo = log.querySelector('.rute-digitando');
    if (antigo) antigo.remove();
    if (!mostrar) return;
    const el = document.createElement('div');
    el.className = 'rute-msg rute-msg--rute rute-digitando';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-label', 'A Sofia está escrevendo');
    const balao = document.createElement('div');
    balao.className = 'rute-balao';
    for (let i = 0; i < 3; i++) balao.append(document.createElement('span'));
    el.append(balao);
    log.append(el);
    rolar();
  }

  // ---------- conversa ----------
  function iniciar() {
    carregar();
    if (!mensagens.length) {
      mensagens.push({ papel: 'rute', texto: raiz.dataset.saudacao || 'Oi! Eu sou a Sofia.' });
      try { sugestoesAtuais = JSON.parse(raiz.dataset.sugestoes || '[]'); } catch (e) { sugestoesAtuais = []; }
      salvar();
    }
    log.replaceChildren();
    mensagens.forEach(m => adicionar(m, false));
    desenharSugestoes();
  }

  async function perguntar(texto) {
    texto = (texto || '').trim();
    if (!texto || aguardando) return;
    aguardando = true;
    enviar.disabled = true;
    entrada.value = '';
    const historico = mensagens.slice(-6).map(m => ({ papel: m.papel, texto: m.texto }));
    const minha = { papel: 'usuario', texto };
    mensagens.push(minha);
    adicionar(minha);
    sugestoesAtuais = [];
    desenharSugestoes();
    digitando(true);
    const inicio = Date.now();
    let resposta;
    try {
      const r = await fetch(raiz.dataset.endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': raiz.dataset.csrf },
        body: JSON.stringify({ mensagem: texto, historico })
      });
      let dados = {};
      try { dados = await r.json(); } catch (e) { /* resposta não era JSON */ }
      if (r.ok && dados.resposta) {
        resposta = { papel: 'rute', texto: dados.resposta, acoes: dados.acoes || [] };
        sugestoesAtuais = Array.isArray(dados.sugestoes) ? dados.sugestoes : [];
      } else if (r.status === 429 || (r.status === 400 && dados.erro)) {
        resposta = { papel: 'rute', texto: dados.erro || 'Muitas mensagens em pouco tempo. Aguarde um instante e tente de novo.' };
      } else {
        resposta = { papel: 'rute', texto: 'Não consegui responder agora. Recarregue a página e tente de novo; se continuar, avise a unidade.' };
      }
    } catch (e) {
      resposta = { papel: 'rute', texto: 'Parece que a conexão falhou. Verifique a internet e tente novamente.' };
    }
    // Uma pausa mínima evita que a resposta "pisque" e deixa a conversa mais natural.
    const espera = reduzMovimento.matches ? 0 : Math.max(0, 450 - (Date.now() - inicio));
    await new Promise(ok => setTimeout(ok, espera));
    digitando(false);
    mensagens.push(resposta);
    adicionar(resposta);
    desenharSugestoes();
    salvar();
    aguardando = false;
    enviar.disabled = false;
    entrada.focus();
  }

  // ---------- abrir e fechar ----------
  function abrir() {
    painel.hidden = false;
    fab.setAttribute('aria-expanded', 'true');
    raiz.classList.add('rute--aberta');
    if (celular.matches) document.body.classList.add('rute-bloqueia');
    rolar();
    entrada.focus();
  }
  function fechar(devolverFoco = true) {
    painel.hidden = true;
    fab.setAttribute('aria-expanded', 'false');
    raiz.classList.remove('rute--aberta');
    document.body.classList.remove('rute-bloqueia');
    if (devolverFoco) fab.focus();
  }
  fab.addEventListener('click', () => (painel.hidden ? abrir() : fechar()));
  $('rute-fechar').addEventListener('click', () => fechar());
  $('rute-limpar').addEventListener('click', () => {
    try { sessionStorage.removeItem(chave); } catch (e) { /* ok */ }
    mensagens = [];
    iniciar();
    entrada.focus();
  });
  painel.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); fechar(); } });
  form.addEventListener('submit', e => { e.preventDefault(); perguntar(entrada.value); });

  iniciar();
  raiz.classList.add('rute--pronta');
})();

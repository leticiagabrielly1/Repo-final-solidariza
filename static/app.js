const menuButton = document.querySelector('.menu-button');
const menu = document.querySelector('#menu');
function setMenu(open) {
  if (!menu || !menuButton) return;
  menu.classList.toggle('open', open);
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
}
menuButton?.addEventListener('click', () => setMenu(!menu.classList.contains('open')));
document.addEventListener('keydown', e => { if (e.key === 'Escape') { setMenu(false); menuButton?.focus(); } });
document.addEventListener('click', e => { if (menu && !menu.contains(e.target) && !menuButton?.contains(e.target)) setMenu(false); });
const mobile = window.matchMedia('(max-width:780px)');
function syncMenu() { if (menu) menu.inert = mobile.matches && !menu.classList.contains('open'); }
if (menu) new MutationObserver(syncMenu).observe(menu, { attributes:true, attributeFilter:['class'] });
mobile.addEventListener('change', syncMenu); syncMenu();
document.querySelectorAll('[data-password]').forEach(button => button.addEventListener('click', () => {
  const input = document.getElementById(button.dataset.password);
  input.type = input.type === 'password' ? 'text' : 'password';
  button.setAttribute('aria-label', input.type === 'password' ? 'Mostrar senha' : 'Ocultar senha');
}));
const form = document.getElementById('item-form');
if (form) {
  const fields = [...form.querySelectorAll('[data-item]')];
  const limit = Number(form.dataset.limit) || Infinity;
  const list = document.getElementById('basket-items');
  function update() {
    let count = 0;
    list.replaceChildren();
    fields.forEach(input => {
      const quantity = Math.max(0, Number(input.value) || 0);
      count += quantity;
      if (quantity > 0) {
        const li = document.createElement('li');
        const name = document.createElement('span');
        const total = document.createElement('strong');
        name.textContent = input.dataset.item;
        total.textContent = '× ' + quantity;
        li.append(name, total); list.append(li);
      }
    });
    document.getElementById('count').textContent = count;
    const progress = document.getElementById('progress');
    if (progress) progress.value = count;
    const message = document.getElementById('limit-message');
    if (message) message.textContent = count > limit ? 'Limite excedido. Remova algumas unidades.' : `${limit - count} unidade(s) disponível(is) para escolher.`;
    const confirm = document.getElementById('confirm-items');
    if (confirm) confirm.disabled = count > limit;
  }
  fields.forEach(input => input.addEventListener('input', update)); update();
}
const search = document.getElementById('product-search');
const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
search?.addEventListener('input', () => {
  let shown = 0;
  document.querySelectorAll('.product').forEach(card => {
    card.hidden = !normalize(card.dataset.name).includes(normalize(search.value));
    if (!card.hidden) shown++;
  });
  document.getElementById('no-results').hidden = shown !== 0;
});
document.getElementById('print')?.addEventListener('click', () => window.print());

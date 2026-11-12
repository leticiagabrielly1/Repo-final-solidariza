
(function(){
'use strict';
const key='rede-acess-v1',html=document.documentElement,body=document.body;
const toggle=document.getElementById('rede-acess-toggle'),panel=document.getElementById('rede-acess-panel');
if(!toggle||!panel)return;
let state={scale:1,contraste:false,escuro:false,espacamento:false,animacoes:false};
try{state={...state,...JSON.parse(localStorage.getItem(key)||'{}')}}catch(e){}
function apply(){
 html.style.setProperty('--rede-scale',state.scale);
 html.classList.toggle('rede-zoom',state.scale!==1);
 body.classList.toggle('rede-alto-contraste',!!state.contraste);
 body.classList.toggle('rede-modo-escuro',!!state.escuro);
 body.classList.toggle('rede-espacamento',!!state.espacamento);
 body.classList.toggle('rede-pausar',!!state.animacoes);
 try{localStorage.setItem(key,JSON.stringify(state))}catch(e){}
}
toggle.addEventListener('click',()=>{const open=panel.hidden;panel.hidden=!open;toggle.setAttribute('aria-expanded',String(open))});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden){panel.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus()}});
panel.addEventListener('click',e=>{
 const b=e.target.closest('button[data-rede-access]');if(!b)return;
 switch(b.dataset.redeAccess){
 case 'mais':state.scale=Math.min(1.5,Math.round((state.scale+.1)*10)/10);break;
 case 'menos':state.scale=Math.max(.8,Math.round((state.scale-.1)*10)/10);break;
 case 'contraste':state.contraste=!state.contraste;break;
 case 'escuro':state.escuro=!state.escuro;break;
 case 'espacamento':state.espacamento=!state.espacamento;break;
 case 'animacoes':state.animacoes=!state.animacoes;break;
 case 'reset':state={scale:1,contraste:false,escuro:false,espacamento:false,animacoes:false};break;
 case 'vlibras':{
 const btn=document.querySelector('[vw-access-button]');
 if(btn){btn.click()}else{alert('VLibras depende de conexão com a internet.')}return;
 }}
 apply();
});
apply();
window.addEventListener('load',()=>{if(window.VLibras){try{new window.VLibras.Widget('https://vlibras.gov.br/app')}catch(e){}}});
})();

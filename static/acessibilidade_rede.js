
(function () {
    'use strict';

    const key = 'rede-acess-v1';
    const html = document.documentElement;

    const toggle = document.getElementById('rede-acess-toggle');
    const panel = document.getElementById('rede-acess-panel');

    if (!toggle || !panel) return;

    let state = {
        scale: 1,
        contraste: false,
        escuro: false,
        espacamento: false,
        animacoes: false
    };

    // Recuperar configurações salvas
    try {
        const saved = JSON.parse(localStorage.getItem(key) || '{}');

        state = {
            ...state,
            ...saved
        };
    } catch (e) {
        console.warn('Erro ao carregar acessibilidade:', e);
    }

    // Validar escala
    state.scale = Number(state.scale) || 1;
    state.scale = Math.max(0.8, Math.min(1.5, state.scale));

    // Elementos que podem ter o tamanho alterado
    const seletorFontes = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'span', 'a', 'li', 'label',
        'button', 'input', 'select', 'textarea',
        'td', 'th', 'small', 'strong', 'b',
        'blockquote', 'figcaption', 'legend'
    ].join(',');

    // Guardar tamanho original das fontes
    function registrarFontes() {
        const elementos = document.querySelectorAll(seletorFontes);

        elementos.forEach(el => {
            // Não alterar botões do painel de acessibilidade
            if (el.closest('.rede-acess')) return;

            // Evitar registrar novamente
            if (el.dataset.redeFonteRegistrada === '1') return;

            const tamanho = parseFloat(
                window.getComputedStyle(el).fontSize
            );

            if (!Number.isFinite(tamanho)) return;

            el.style.setProperty(
                '--rede-original-font',
                tamanho + 'px'
            );

            el.dataset.redeFonteRegistrada = '1';
        });
    }

    // Aplicar configurações
    function apply() {
        const body = document.body;

        if (!body) return;

        // Desativar zoom temporariamente para registrar fontes
        html.classList.remove('rede-zoom');

        // Registrar fontes ainda não registradas
        registrarFontes();

        // Aplicar escala
        html.style.setProperty(
            '--rede-scale',
            String(state.scale)
        );

        html.classList.toggle(
            'rede-zoom',
            state.scale !== 1
        );

        // Alto contraste
        body.classList.toggle(
            'rede-alto-contraste',
            Boolean(state.contraste)
        );

        // Modo escuro
        body.classList.toggle(
            'rede-modo-escuro',
            Boolean(state.escuro)
        );

        // Espaçamento
        body.classList.toggle(
            'rede-espacamento',
            Boolean(state.espacamento)
        );

        // Pausar animações
        body.classList.toggle(
            'rede-pausar',
            Boolean(state.animacoes)
        );

        // Salvar configurações
        try {
            localStorage.setItem(
                key,
                JSON.stringify(state)
            );
        } catch (e) {
            console.warn('Erro ao salvar acessibilidade:', e);
        }
    }

    // Abrir e fechar painel
    toggle.addEventListener('click', () => {
        const aberto = panel.hidden;

        panel.hidden = !aberto;

        toggle.setAttribute(
            'aria-expanded',
            String(aberto)
        );
    });

    // Fechar painel com ESC
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && !panel.hidden) {
            panel.hidden = true;

            toggle.setAttribute(
                'aria-expanded',
                'false'
            );

            toggle.focus();
        }
    });

    // Funções dos botões
    panel.addEventListener('click', e => {
        const botao = e.target.closest(
            'button[data-rede-access]'
        );

        if (!botao) return;

        const acao = botao.dataset.redeAccess;

        switch (acao) {

            // AUMENTAR LETRAS
            case 'mais':
                state.scale = Math.min(
                    1.5,
                    Math.round((state.scale + 0.1) * 10) / 10
                );
                break;

            // DIMINUIR LETRAS
            case 'menos':
                state.scale = Math.max(
                    0.8,
                    Math.round((state.scale - 0.1) * 10) / 10
                );
                break;

            // ALTO CONTRASTE
            case 'contraste':
                state.contraste = !state.contraste;
                break;

            // MODO ESCURO
            case 'escuro':
                state.escuro = !state.escuro;
                break;

            // ESPAÇAMENTO
            case 'espacamento':
                state.espacamento = !state.espacamento;
                break;

            // PAUSAR ANIMAÇÕES
            case 'animacoes':
                state.animacoes = !state.animacoes;
                break;

            // RESTAURAR PADRÃO
            case 'reset':
                state = {
                    scale: 1,
                    contraste: false,
                    escuro: false,
                    espacamento: false,
                    animacoes: false
                };
                break;

            // VLIBRAS
            case 'vlibras':
                const btnVLibras = document.querySelector(
                    '[vw-access-button]'
                );

                if (btnVLibras) {
                    btnVLibras.click();
                } else {
                    alert('VLibras não está disponível.');
                }

                return;

            default:
                return;
        }

        apply();
    });

    // Aplicar configurações iniciais
    apply();

    // Registrar fontes após carregar a página
    window.addEventListener('load', () => {
        registrarFontes();

        if (window.VLibras) {
            try {
                if (!document.querySelector('[vw-plugin-wrapper]')) {
                    new window.VLibras.Widget(
                        'https://vlibras.gov.br/app'
                    );
                }
            } catch (e) {
                console.warn('Erro ao iniciar VLibras:', e);
            }
        }
    });

})();

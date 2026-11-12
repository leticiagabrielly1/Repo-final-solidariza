
(function () {
    'use strict';

    const key = 'rede-acess-v1';
    const html = document.documentElement;
    const body = document.body;

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

    try {
        state = {
            ...state,
            ...JSON.parse(localStorage.getItem(key) || '{}')
        };
    } catch (e) {}

    // Guarda os tamanhos originais das fontes
    function registrarFontes() {
        const elementos = document.querySelectorAll(
            'h1,h2,h3,h4,h5,h6,p,span,a,li,label,' +
            'button,input,select,textarea,td,th,' +
            'small,strong,b,blockquote,figcaption,legend'
        );

        elementos.forEach(el => {
            if (el.dataset.redeFonteRegistrada) return;

            const tamanho = parseFloat(
                getComputedStyle(el).fontSize
            );

            if (!Number.isFinite(tamanho)) return;

            el.style.setProperty(
                '--rede-original-font',
                tamanho + 'px'
            );

            el.dataset.redeFonteRegistrada = '1';
        });
    }

    function apply() {
        // Registra os tamanhos antes de ativar o zoom
        if (!html.classList.contains('rede-zoom')) {
            registrarFontes();
        }

        html.style.setProperty(
            '--rede-scale',
            state.scale
        );

        html.classList.toggle(
            'rede-zoom',
            state.scale !== 1
        );

        body.classList.toggle(
            'rede-alto-contraste',
            !!state.contraste
        );

        body.classList.toggle(
            'rede-modo-escuro',
            !!state.escuro
        );

        body.classList.toggle(
            'rede-espacamento',
            !!state.espacamento
        );

        body.classList.toggle(
            'rede-pausar',
            !!state.animacoes
        );

        try {
            localStorage.setItem(
                key,
                JSON.stringify(state)
            );
        } catch (e) {}
    }

    toggle.addEventListener('click', () => {
        const open = panel.hidden;

        panel.hidden = !open;

        toggle.setAttribute(
            'aria-expanded',
            String(open)
        );
    });

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && !panel.hidden) {
            panel.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
            toggle.focus();
        }
    });

    panel.addEventListener('click', e => {
        const b = e.target.closest(
            'button[data-rede-access]'
        );

        if (!b) return;

        switch (b.dataset.redeAccess) {
            case 'mais':
                state.scale = Math.min(
                    1.5,
                    Math.round((state.scale + .1) * 10) / 10
                );
                break;

            case 'menos':
                state.scale = Math.max(
                    .8,
                    Math.round((state.scale - .1) * 10) / 10
                );
                break;

            case 'contraste':
                state.contraste = !state.contraste;
                break;

            case 'escuro':
                state.escuro = !state.escuro;
                break;

            case 'espacamento':
                state.espacamento = !state.espacamento;
                break;

            case 'animacoes':
                state.animacoes = !state.animacoes;
                break;

            case 'reset':
                state = {
                    scale: 1,
                    contraste: false,
                    escuro: false,
                    espacamento: false,
                    animacoes: false
                };
                break;

            case 'vlibras':
                const btn = document.querySelector(
                    '[vw-access-button]'
                );

                if (btn) {
                    btn.click();
                } else {
                    alert('VLibras não está disponível.');
                }
                return;
        }

        apply();
    });

    apply();

    window.addEventListener('load', () => {
        if (window.VLibras) {
            try {
                if (!document.querySelector('[vw-plugin-wrapper]')) {
                    new window.VLibras.Widget(
                        'https://vlibras.gov.br/app'
                    );
                }
            } catch (e) {}
        }
    });
})();

/* Funções de renderização de campos compartilhadas entre o modal individual
 * de envio (history.html) e a tela de envio em lote (enviar_diario_trade_lote.html)
 * ao Diário de Trade. Namespace window.DiarioTrade para não poluir o escopo global
 * nos dois templates que incluem este arquivo. */
window.DiarioTrade = (function() {

    function opts(list, selected) {
        return list.map(function(v) {
            return '<option value="' + v + '"' + (v === selected ? ' selected' : '') + '>' + v + '</option>';
        }).join('');
    }

    function exitRowHtml(ex, idx) {
        ex = ex || {};
        return '<tr class="dt-exit-row" data-idx="' + idx + '">' +
            '<td><input type="date" class="form-control form-control-sm dt-exit-date" value="' + (ex.date || '') + '"></td>' +
            '<td><input type="number" class="form-control form-control-sm dt-exit-qty" value="' + (ex.qty != null ? ex.qty : '') + '" min="1" step="1"></td>' +
            '<td><input type="number" class="form-control form-control-sm dt-exit-price" value="' + (ex.price != null ? ex.price : '') + '" step="0.01"></td>' +
            '<td><button type="button" class="btn btn-sm btn-danger" onclick="this.closest(\'tr\').remove()">🗑</button></td>' +
            '</tr>';
    }

    // Estratégia/Subjacente: <select> com a lista fixa da API (settings.strategies/
    // settings.assets, obtida via GET /me) quando disponível; texto livre como
    // fallback se a lista não pôde ser carregada. idPrefix diferencia instâncias
    // que coexistem no mesmo DOM (ex.: formulário simplificado vs. completo, ou
    // várias linhas da tela de envio em lote).
    function strategyFieldHtml(d, idPrefix) {
        var id = idPrefix + 'strategy';
        if (d.strategies && d.strategies.length) {
            return '<select id="' + id + '" class="form-control form-control-sm">' + opts(d.strategies, d.strategy) + '</select>';
        }
        return '<input type="text" id="' + id + '" class="form-control form-control-sm" value="' + (d.strategy || '') + '">';
    }

    function underlyingFieldHtml(d, idPrefix) {
        var id = idPrefix + 'underlying';
        if (d.assets && d.assets.length) {
            var list = d.assets.slice();
            // Ativo local fora da lista fixa da API: inclui como opção extra no
            // topo em vez de descartar o dado (a API pode rejeitar no envio,
            // mas o usuário vê e decide, em vez de perder a informação em silêncio).
            if (d.underlying && list.indexOf(d.underlying) === -1) {
                list = [d.underlying].concat(list);
            }
            return '<select id="' + id + '" class="form-control form-control-sm">' + opts(list, d.underlying) + '</select>';
        }
        return '<input type="text" id="' + id + '" class="form-control form-control-sm" value="' + (d.underlying || '') + '">';
    }

    // Setups: checkboxes com a lista padrão do usuário (settings.setups via
    // GET /me) quando disponível; texto livre como fallback se a lista não
    // pôde ser carregada.
    function buildSetupsFieldHtml(d, idPrefix) {
        var groupId = idPrefix + 'setups-group';
        var cbClass = idPrefix + 'setup-cb';
        var textId = idPrefix + 'setups';
        if (d.setups_options && d.setups_options.length) {
            var selected = d.setups || [];
            var boxes = d.setups_options.map(function(s, i) {
                var id = idPrefix + 'setup-' + i;
                var checked = selected.indexOf(s) !== -1 ? ' checked' : '';
                return '<div class="form-check" style="display:flex; align-items:center; gap:.4rem;">' +
                    '<input class="form-check-input ' + cbClass + '" type="checkbox" id="' + id + '" value="' + s + '"' + checked + ' style="margin:0;">' +
                    '<label class="form-check-label" for="' + id + '" style="font-size:.82rem; cursor:pointer; margin:0;">' + s + '</label>' +
                    '</div>';
            }).join('');
            return '<div id="' + groupId + '" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(160px, 1fr)); gap:.5rem .8rem;">' + boxes + '</div>';
        }
        return '<input type="text" id="' + textId + '" class="form-control form-control-sm" value="' + ((d.setups || []).join(', ')) + '" placeholder="Recomendação, Price action...">';
    }

    // Lê o valor atual de Setups do DOM (checkboxes marcados, ou o texto livre
    // separado por vírgula quando a lista não pôde ser carregada).
    function readSetups(idPrefix) {
        var textEl = document.getElementById(idPrefix + 'setups');
        if (textEl) {
            return textEl.value.split(',').map(function(s) { return s.trim(); }).filter(Boolean);
        }
        return Array.from(document.querySelectorAll('.' + idPrefix + 'setup-cb:checked')).map(function(cb) { return cb.value; });
    }

    return {
        opts: opts,
        exitRowHtml: exitRowHtml,
        strategyFieldHtml: strategyFieldHtml,
        underlyingFieldHtml: underlyingFieldHtml,
        buildSetupsFieldHtml: buildSetupsFieldHtml,
        readSetups: readSetups,
    };
})();

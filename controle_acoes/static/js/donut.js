/* donut.js — donuts padronizados (estilo "Receitas por Categoria"):
 *   • total dos itens visíveis no CENTRO do donut;
 *   • legenda em LISTA abaixo: bolinha + nome à esquerda, R$ e (%) à direita;
 *   • clique na linha esconde/mostra a fatia; hover destaca a fatia.
 * Uso: donutChart('canvasId', labels, values, colors,
 *                 { legendId: 'divId', centerLabel: 'Total' });
 * Requer Chart.js já carregado.
 */
(function () {
    'use strict';

    // ── estilos da legenda-lista (injetados uma única vez) ────────────────────
    if (!document.getElementById('donut-css')) {
        var st = document.createElement('style');
        st.id = 'donut-css';
        st.textContent =
            '.donut-legend{margin-top:.6rem;font-size:.85rem;}' +
            '.dl-row{display:flex;align-items:center;gap:.55rem;padding:.42rem .55rem;' +
            'border-top:1px solid rgba(148,163,184,.14);cursor:pointer;border-radius:6px;}' +
            '.dl-row:first-child{border-top:none;}' +
            '.dl-row:hover{background:rgba(148,163,184,.10);}' +
            '.dl-row.off{opacity:.4;}' +
            '.dl-row.off .dl-name{text-decoration:line-through;}' +
            '.dl-dot{width:12px;height:12px;border-radius:4px;flex:none;}' +
            '.dl-name{flex:1;color:var(--text-primary,#e2e8f0);white-space:nowrap;' +
            'overflow:hidden;text-overflow:ellipsis;}' +
            '.dl-val{font-weight:700;color:var(--text-primary,#e2e8f0);white-space:nowrap;}' +
            '.dl-pct{color:var(--text-secondary,#94a3b8);font-size:.78rem;min-width:52px;' +
            'text-align:right;white-space:nowrap;}';
        document.head.appendChild(st);
    }

    function fmtBRLd(v) {
        return 'R$ ' + Number(v || 0).toLocaleString('pt-BR',
            { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // ── plugin: total (dos visíveis) no centro do donut ───────────────────────
    var DonutCenter = {
        id: 'donutCenter',
        afterDraw: function (chart) {
            var opts = chart.options.plugins && chart.options.plugins.donutCenter;
            if (!opts || opts.enabled === false) return;
            var meta = chart.getDatasetMeta(0);
            if (!meta || !meta.data || !meta.data.length) return;
            var x = meta.data[0].x, y = meta.data[0].y;
            var total = 0;
            (chart.data.datasets[0].data || []).forEach(function (v, i) {
                if (chart.getDataVisibility(i)) total += Number(v) || 0;
            });
            var ctx = chart.ctx;
            // valor encolhe se não couber no miolo
            var inner = (meta.data[0].innerRadius || 60) * 2 - 16;
            var vs = opts.valueSize || 16;
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = opts.subColor || 'rgba(148,163,184,.95)';
            ctx.font = '600 ' + (opts.subSize || 10) + 'px Inter,system-ui,sans-serif';
            ctx.fillText((opts.label || 'TOTAL').toUpperCase(), x, y - 12);
            ctx.fillStyle = opts.color || getComputedStyle(document.documentElement)
                .getPropertyValue('--text-primary').trim() || '#f1f5f9';
            var txt = fmtBRLd(total);
            do {
                ctx.font = '700 ' + vs + 'px Inter,system-ui,sans-serif';
                if (ctx.measureText(txt).width <= inner || vs <= 10) break;
                vs -= 1;
            } while (true);
            ctx.fillText(txt, x, y + 8);
            ctx.restore();
        }
    };

    // ── legenda-lista interativa ──────────────────────────────────────────────
    function renderDonutLegend(chart, el) {
        function build() {
            var ds = chart.data.datasets[0];
            var sum = 0;
            ds.data.forEach(function (v, i) {
                if (chart.getDataVisibility(i)) sum += Number(v) || 0;
            });
            el.innerHTML = chart.data.labels.map(function (lb, i) {
                var v = Number(ds.data[i]) || 0;
                var off = !chart.getDataVisibility(i);
                var pct = (!off && sum > 0)
                    ? (v / sum * 100).toFixed(1).replace('.', ',') + '%' : '—';
                var color = Array.isArray(ds.backgroundColor)
                    ? ds.backgroundColor[i % ds.backgroundColor.length]
                    : ds.backgroundColor;
                return '<div class="dl-row' + (off ? ' off' : '') + '" data-i="' + i + '" ' +
                       'title="Clique para ocultar/mostrar a fatia">' +
                       '<span class="dl-dot" style="background:' + color + '"></span>' +
                       '<span class="dl-name">' + lb + '</span>' +
                       '<span class="dl-val">' + fmtBRLd(v) + '</span>' +
                       '<span class="dl-pct">(' + pct + ')</span></div>';
            }).join('');
            el.querySelectorAll('.dl-row').forEach(function (row) {
                var i = +row.dataset.i;
                row.addEventListener('click', function () {
                    chart.toggleDataVisibility(i);
                    chart.update();
                    build();
                });
                row.addEventListener('mouseenter', function () {
                    if (!chart.getDataVisibility(i)) return;
                    chart.setActiveElements([{ datasetIndex: 0, index: i }]);
                    chart.update();
                });
                row.addEventListener('mouseleave', function () {
                    chart.setActiveElements([]);
                    chart.update();
                });
            });
        }
        build();
    }

    // ── fábrica ───────────────────────────────────────────────────────────────
    window.donutChart = function (canvasId, labels, values, colors, opts) {
        opts = opts || {};
        var el = document.getElementById(canvasId);
        if (!el) return null;
        // filtra valores <= 0 (fatias invisíveis só poluem a legenda)
        var L = [], V = [], C = [];
        (labels || []).forEach(function (lb, i) {
            var v = Number(values[i]) || 0;
            if (v > 0.005) {
                L.push(lb); V.push(v);
                C.push(colors[i % colors.length]);
            }
        });
        var chart = new Chart(el.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: L,
                datasets: [{
                    data: V,
                    backgroundColor: C,
                    borderWidth: 2,
                    borderColor: opts.borderColor || 'rgba(15,23,42,.85)',
                    hoverOffset: 10,
                    hoverBorderColor: 'rgba(255,255,255,.35)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: opts.cutout || '68%',
                layout: { padding: 10 },
                plugins: {
                    legend: { display: false },
                    datalabels: { display: false },
                    donutCenter: { enabled: true, label: opts.centerLabel || 'Total' },
                    tooltip: {
                        callbacks: {
                            label: function (c) {
                                var sum = 0;
                                c.dataset.data.forEach(function (v, i) {
                                    if (c.chart.getDataVisibility(i)) sum += Number(v) || 0;
                                });
                                var pct = sum > 0
                                    ? (c.parsed / sum * 100).toFixed(1).replace('.', ',') : '0,0';
                                return ' ' + c.label + ': ' + fmtBRLd(c.parsed) + ' (' + pct + '%)';
                            }
                        }
                    }
                }
            },
            plugins: [DonutCenter]
        });
        if (opts.legendId) {
            var lg = document.getElementById(opts.legendId);
            if (lg) renderDonutLegend(chart, lg);
        }
        return chart;
    };
})();

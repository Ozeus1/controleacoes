/* Botão "Gráfico Completo": abre o gráfico do ativo em acoes.receberbemevinhos.com.br (candles de 5min do dia)
 * já com os walls desenhados como linhas horizontais, via sufixo _sup(preço,cor,texto;...).
 *
 * Linhas = as mesmas do gráfico interno ("Ver Gráfico"): os 16 walls (lime, "Wall"), o MidWall entre walls
 * consecutivos (gray, "MidWall"), as 2 bandas de Fibonacci 11,8% (dimgray, "Fibo") e, quando o payload tem,
 * Gama máx (green), Gama mín (red) e Flip (yellow). O texto não pode ter vírgula/; (separadores do formato).
 * O número ("api_key") vem da meta "receberbem-num" (Configuração > Gráfico Completo).
 * Depende de walls_export.js (extrairTop16Walls). */
(function (global) {
  'use strict';

  function n2(v) { return Number(v).toFixed(2); }

  function montarLinhas(d) {
    var top = extrairTop16Walls(d), linhas = [];
    top.forEach(function (w) { linhas.push(n2(w.strike) + ',lime,Wall'); });
    for (var i = 0; i < top.length - 1; i++) {
      var a = top[i].strike, b = top[i + 1].strike, meio = (a + b) / 2, banda = (b - a) * 0.118;
      linhas.push(n2(meio) + ',gray,MidWall');
      linhas.push(n2(meio - banda) + ',dimgray,Fibo');
      linhas.push(n2(meio + banda) + ',dimgray,Fibo');
    }
    if (d.gamma_max && isFinite(d.gamma_max.s)) linhas.push(n2(d.gamma_max.s) + ',green,GamaMax');
    if (d.gamma_min && isFinite(d.gamma_min.s)) linhas.push(n2(d.gamma_min.s) + ',red,GamaMin');
    if (isFinite(d.flip)) linhas.push(n2(d.flip) + ',yellow,Flip');
    return linhas;
  }

  function urlGraficoCompleto(ticker, dados) {
    var linhas = montarLinhas(dados);
    if (!linhas.length) throw new Error('Sem walls para desenhar no gráfico.');
    var meta = document.querySelector('meta[name="receberbem-num"]');
    var num = meta ? (meta.content || '').trim() : '';
    return 'https://acoes.receberbemevinhos.com.br/?action=ticker&view=' + encodeURIComponent(ticker) +
      '&range=1d&interval=5m' + (num ? '&api_key=' + encodeURIComponent(num) : '') +
      '_sup(' + linhas.join(';') + ')';
  }

  /** Abre a aba no clique (evita bloqueio de pop-up) e redireciona quando os dados chegam.
   * @param {string} ticker símbolo usado no site (ex.: PETR4, ^BVSP, USDBRL=X)
   * @param {Function} obterDados devolve o payload dos walls (ou uma Promise dele)
   * @returns {Promise} rejeita com Error se não foi possível montar o gráfico */
  function abrirGraficoCompletoWalls(ticker, obterDados) {
    var win = window.open('about:blank', '_blank'), aberto = false;
    function fim() { if (!aberto && win) win.close(); }
    return Promise.resolve().then(obterDados).then(function (dados) {
      var url = urlGraficoCompleto(ticker, dados);
      aberto = true;
      if (win) win.location.href = url; else window.open(url, '_blank');
    }).then(fim, function (e) { fim(); throw e; });
  }

  global.abrirGraficoCompletoWalls = abrirGraficoCompletoWalls;
})(window);

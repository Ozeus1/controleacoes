/* Exportação de "Jumba Walls" para indicador NTSL do Profit.
 *
 * Formato de referência (walls.txt fornecido pelo usuário): até 64 linhas
 * fixas (lineN / lineNColor / lineNWidth / lineNStyle) — 16 "walls" (strikes
 * de maior gama líquido em módulo, ordenados por strike), 15 conjuntos de
 * MidWall + duas bandas de Fibonacci (um por par de walls consecutivos), e
 * as 3 finais fixas: Gamma Máximo, Gamma Mínimo e Flip.
 *
 * Regras extraídas por engenharia reversa do arquivo de exemplo:
 *   - MidWall = ponto médio exato entre dois walls consecutivos.
 *   - Bandas Fibo = MidWall ± 11,8% do passo entre os dois walls (0.118 —
 *     nível de Fibonacci comum, confirmado batendo em todos os 15 pares).
 *   - lineWidth de cada wall (1/2/3) é proporcional à magnitude do gama
 *     líquido |call - put| daquele strike dentro da faixa exportada —
 *     tercis: o terço mais fraco leva 1, o do meio 2, o mais forte 3.
 *   - A condição de data no indicador usa o dia seguinte ao pregão de
 *     referência (dados de sexta → indicador vale a partir de segunda),
 *     não a própria data dos dados.
 */
(function (global) {
  'use strict';

  var CORES = {
    clWall: 'clLime',
    clMidWall: 'clGray',
    clMidWallFibo: 'clDkGray',
    clFlip: 'clYellow',
    clMaxGamma: 'clGreen',
    clMinGamma: 'clRed',
  };

  function proximoDiaUtil(isoDate) {
    var d = isoDate ? new Date(isoDate + 'T00:00:00') : new Date();
    do {
      d.setDate(d.getDate() + 1);
    } while (d.getDay() === 0 || d.getDay() === 6);
    return { y: d.getFullYear(), m: d.getMonth() + 1, dia: d.getDate() };
  }

  function fmtNum(v) {
    // NTSL usa ponto decimal; strikes/gama já vêm em ponto do JSON.
    return Number(v).toFixed(3);
  }

  /**
   * Extrai os até 16 "walls" principais (maior |gama líquido|, reordenados
   * por strike) a partir do payload da API — mesma lógica usada tanto na
   * exportação do .txt quanto no gráfico de candles com os walls plotados.
   *
   * @param {Object} d payload da API: precisa de d.paredes OU d.walls (o
   *                   Trader IND/DOL não tem 'paredes' — usa 'walls' somando
   *                   os 3 grupos atual+proximo+demais por strike).
   * @returns {Array<{strike:number,total:number,largura:number}>}
   */
  function extrairTop16Walls(d) {
    var paredes;
    if (d.paredes && d.paredes.length) {
      paredes = d.paredes.filter(function (p) {
        return p && isFinite(p.strike) && isFinite(p.total);
      });
    } else {
      paredes = (d.walls || [])
        .filter(function (w) { return w && isFinite(w.strike); })
        .map(function (w) {
          var total = (w.atual || 0) + (w.proximo || 0) + (w.demais || 0);
          return { strike: w.strike, total: total };
        });
    }
    var top16 = paredes.slice()
      .sort(function (a, b) { return Math.abs(b.total) - Math.abs(a.total); })
      .slice(0, 16)
      .sort(function (a, b) { return a.strike - b.strike; });

    var mags = top16.map(function (p) { return Math.abs(p.total); }).sort(function (a, b) { return a - b; });
    function largura(mag) {
      if (!mags.length) return 1;
      var i = mags.indexOf(mag);
      var pos = i / Math.max(mags.length - 1, 1);
      if (pos < 1 / 3) return 1;
      if (pos < 2 / 3) return 2;
      return 3;
    }
    top16.forEach(function (p) { p.largura = largura(Math.abs(p.total)); });
    return top16;
  }

  /**
   * Monta o texto do indicador NTSL a partir dos dados já calculados na
   * tela (paredes por strike, flip, gamma_max/min) — não faz nenhuma
   * requisição nova, só reformata o que o usuário já está vendo.
   *
   * @param {Object} d        payload da API (mesmo formato de /api/market-gamma
   *                          e /api/trader-fut): precisa de d.flip, d.gamma_max,
   *                          d.gamma_min, d.data_ref, e de d.paredes OU d.walls.
   * @param {string[]} ativos lista de nomes aceitos por GetAsset() no Profit
   *                          (ex.: ['PETR4'] ou ['WINFUT','INDFUT','WINV26','INDV26']).
   * @returns {string} conteúdo completo do .txt
   */
  function gerarWallsNTSL(d, ativos) {
    var top16 = extrairTop16Walls(d);
    var linhas = [];   // {valor, cor, largura}
    top16.forEach(function (p) {
      linhas.push({ valor: p.strike, cor: 'clWall', largura: p.largura, estilo: 0 });
    });
    for (var i = 0; i < top16.length - 1; i++) {
      var a = top16[i].strike, b = top16[i + 1].strike;
      var passo = b - a, meio = (a + b) / 2, banda = passo * 0.118;
      linhas.push({ valor: meio, cor: 'clMidWall', largura: 1, estilo: 0 });
      linhas.push({ valor: meio - banda, cor: 'clMidWallFibo', largura: 1, estilo: 0 });
      linhas.push({ valor: meio + banda, cor: 'clMidWallFibo', largura: 1, estilo: 0 });
    }
    if (d.gamma_max && isFinite(d.gamma_max.s)) {
      linhas.push({ valor: d.gamma_max.s, cor: 'clMaxGamma', largura: 3, estilo: 0 });
    }
    if (d.gamma_min && isFinite(d.gamma_min.s)) {
      linhas.push({ valor: d.gamma_min.s, cor: 'clMinGamma', largura: 3, estilo: 0 });
    }
    if (isFinite(d.flip)) {
      linhas.push({ valor: d.flip, cor: 'clFlip', largura: 2, estilo: 0 });
    }
    linhas = linhas.slice(0, 64);   // limite físico do indicador (64 plots)
    var n = linhas.length;

    var out = [];
    out.push('var');
    // As 6 cores usadas no BEGIN (clWall := clLime; etc.) precisam estar
    // declaradas aqui — sem isso o NTSL recusa compilar por variável não
    // declarada (bug encontrado: o arquivo gerado pulava direto para as
    // linhas, atribuindo cor a variáveis nunca declaradas).
    Object.keys(CORES).forEach(function (k) {
      out.push('  ' + k + ' : integer;');
    });
    for (var k = 1; k <= n; k++) {
      out.push('  line' + k + ' : float;');
      out.push('  line' + k + 'Color : integer;');
      out.push('  line' + k + 'Width : integer;');
      out.push('  line' + k + 'Style : integer;');
    }
    out.push('');
    out.push('BEGIN');
    Object.keys(CORES).forEach(function (k) {
      out.push('  ' + k + ' := ' + CORES[k] + ';');
    });
    out.push('');
    linhas.forEach(function (l, idx) {
      var k = idx + 1;
      out.push('  line' + k + ' := ' + fmtNum(l.valor) + ';');
      out.push('  line' + k + 'Color := ' + l.cor + ';');
      out.push('  line' + k + 'Width := ' + l.largura + ';');
      out.push('  line' + k + 'Style := ' + l.estilo + ';');
    });
    out.push('');

    var prox = proximoDiaUtil(d.data_ref);
    var condAtivos = (ativos || []).map(function (a) {
      return '(GetAsset() = "' + a + '")';
    }).join(' or ');
    out.push('  if (((Date = ELDate(' + prox.y + ', ' +
      String(prox.m).padStart(2, '0') + ', ' + String(prox.dia).padStart(2, '0') +
      ')) and (Time >= 900)) and (' + condAtivos + ')) then');
    out.push('  begin');
    for (var k2 = 1; k2 <= n; k2++) {
      out.push('    SetPlotColor(' + k2 + ', line' + k2 + 'Color);');
      out.push('    SetPlotWidth(' + k2 + ', line' + k2 + 'Width);');
      out.push('    SetPlotStyle(' + k2 + ', line' + k2 + 'Style);');
      out.push('    Plot' + (k2 === 1 ? '' : k2) + '(line' + k2 + ');');
    }
    out.push('  end;');
    out.push('');
    out.push('  if (Time > 1900) then');
    out.push('    begin');
    for (var k3 = 1; k3 <= n; k3++) {
      out.push('      NoPlot(' + k3 + ');');
    }
    out.push('    end;');
    out.push('END;');
    return out.join('\r\n');
  }

  function baixarTxt(conteudo, nomeArquivo) {
    var blob = new Blob([conteudo], { type: 'text/plain;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = nomeArquivo;
    document.body.appendChild(a); a.click();
    setTimeout(function () { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
  }

  global.gerarWallsNTSL = gerarWallsNTSL;
  global.extrairTop16Walls = extrairTop16Walls;
  global.baixarTxt = baixarTxt;
})(window);

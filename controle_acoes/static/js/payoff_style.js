/* Estilo visual do gráfico de payoff — padrão "Jumba".
 *
 * As três telas que desenham payoff (Simulador Gráfico, Com Liquidez e
 * Cadeia de Opções) tinham cada uma sua cópia do mesmo desenho em canvas.
 * As primitivas visuais ficam aqui para as três compartilharem a mesma
 * aparência; o cálculo do payoff continua em cada tela (cada uma tem suas
 * regras de perna/vencimento).
 *
 * Diferenças em relação ao desenho antigo, seguindo a referência:
 *   - Áreas de lucro/prejuízo sólidas e saturadas (antes 0.18 de alpha,
 *     quase invisíveis) e recortadas na própria curva, não no meio do
 *     retângulo — é o que dá o contorno cheio característico.
 *   - Curva única em amarelo (linha de vencimento) em vez de trocar de
 *     cor por trecho: na referência a cor comunica o vencimento, e o
 *     lucro/prejuízo já é lido pelo preenchimento.
 *   - Marcos (spot, breakeven, strike) viram "pílulas" legíveis em vez de
 *     texto solto colado no eixo.
 */
(function (global) {
  'use strict';

  var CORES = {
    venc:      '#f2c94c',                    // curva no vencimento
    atual:     '#e8edf5',                    // curva "hoje" (quando existir)
    lucro:     'rgba(22, 199, 132, 0.34)',
    prejuizo:  'rgba(235, 87, 87, 0.30)',
    zero:      'rgba(226, 232, 240, 0.55)',
    grade:     'rgba(148, 163, 184, 0.10)',
    borda:     'rgba(148, 163, 184, 0.18)',
    eixoTxt:   'rgba(148, 163, 184, 0.90)',
    strike:    'rgba(148, 163, 184, 0.45)',
    be:        '#94a3b8',
    spot:      '#3b82f6',
    faixa:     'rgba(120, 150, 200, 0.07)'   // realce entre marcos
  };

  /** Pílula de rótulo (Spot / Break Even / K=...) como na referência. */
  function pilula(ctx, texto, x, y, corFundo, corTexto, opts) {
    opts = opts || {};
    var fonte = opts.fonte || 'bold 10px sans-serif';
    ctx.save();
    ctx.font = fonte;
    var padX = 6, padY = 3;
    var w = ctx.measureText(texto).width + padX * 2;
    var h = 15;
    var bx = x - w / 2, by = y - h / 2;
    // não deixa a pílula sair da área do canvas
    if (opts.limites) {
      var lim = opts.limites;
      if (bx < lim.min) bx = lim.min;
      if (bx + w > lim.max) bx = lim.max - w;
    }
    var r = 4;
    ctx.beginPath();
    ctx.moveTo(bx + r, by);
    ctx.arcTo(bx + w, by, bx + w, by + h, r);
    ctx.arcTo(bx + w, by + h, bx, by + h, r);
    ctx.arcTo(bx, by + h, bx, by, r);
    ctx.arcTo(bx, by, bx + w, by, r);
    ctx.closePath();
    ctx.fillStyle = corFundo;
    ctx.fill();
    if (opts.borda) {
      ctx.strokeStyle = opts.borda;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    ctx.fillStyle = corTexto;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(texto, bx + w / 2, by + h / 2 + 0.5);
    ctx.restore();
  }

  /** Grade + eixo zero + borda da área de plotagem. */
  function grade(ctx, geo) {
    var W = geo.W, H = geo.H, PAD = geo.PAD, cW = geo.cW, cH = geo.cH;
    ctx.save();
    ctx.strokeStyle = CORES.grade;
    ctx.lineWidth = 1;
    for (var i = 0; i <= 6; i++) {
      var yp = PAD.top + i * cH / 6;
      ctx.beginPath(); ctx.moveTo(PAD.left, yp); ctx.lineTo(W - PAD.right, yp); ctx.stroke();
    }
    for (var j = 0; j <= 8; j++) {
      var xp = PAD.left + j * cW / 8;
      ctx.beginPath(); ctx.moveTo(xp, PAD.top); ctx.lineTo(xp, H - PAD.bottom); ctx.stroke();
    }
    ctx.restore();
  }

  function eixoZero(ctx, geo, y0) {
    ctx.save();
    ctx.strokeStyle = CORES.zero;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(geo.PAD.left, y0);
    ctx.lineTo(geo.W - geo.PAD.right, y0);
    ctx.stroke();
    ctx.restore();
  }

  function borda(ctx, geo) {
    ctx.save();
    ctx.strokeStyle = CORES.borda;
    ctx.lineWidth = 1;
    ctx.strokeRect(geo.PAD.left, geo.PAD.top, geo.cW, geo.cH);
    ctx.restore();
  }

  /**
   * Áreas de lucro e prejuízo, recortadas pela própria curva.
   * Sarr/Parr: série; xPx/yPx: projeções; y0: pixel do zero.
   */
  function areas(ctx, geo, Sarr, Parr, xPx, yPx, y0) {
    var PAD = geo.PAD, cW = geo.cW, H = geo.H;

    function traca() {
      ctx.beginPath();
      ctx.moveTo(xPx(Sarr[0]), y0);
      for (var i = 0; i < Sarr.length; i++) ctx.lineTo(xPx(Sarr[i]), yPx(Parr[i]));
      ctx.lineTo(xPx(Sarr[Sarr.length - 1]), y0);
      ctx.closePath();
    }

    // lucro: parte da curva acima do zero
    ctx.save();
    ctx.beginPath();
    ctx.rect(PAD.left, PAD.top, cW, Math.max(y0 - PAD.top, 0));
    ctx.clip();
    traca();
    ctx.fillStyle = CORES.lucro;
    ctx.fill();
    ctx.restore();

    // prejuízo: parte abaixo do zero
    ctx.save();
    ctx.beginPath();
    ctx.rect(PAD.left, y0, cW, Math.max(H - PAD.bottom - y0, 0));
    ctx.clip();
    traca();
    ctx.fillStyle = CORES.prejuizo;
    ctx.fill();
    ctx.restore();
  }

  /** Curva do payoff no vencimento — linha única, com brilho suave. */
  function curva(ctx, Sarr, Parr, xPx, yPx, cor, largura) {
    ctx.save();
    ctx.strokeStyle = cor || CORES.venc;
    ctx.lineWidth = largura || 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.shadowColor = cor || CORES.venc;
    ctx.shadowBlur = 6;
    ctx.beginPath();
    for (var i = 0; i < Sarr.length; i++) {
      var x = xPx(Sarr[i]), y = yPx(Parr[i]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();
  }

  /** Linha vertical pontilhada de um marco (strike, BE, spot). */
  function marco(ctx, geo, x, cor, tracejado, largura) {
    ctx.save();
    ctx.setLineDash(tracejado || [4, 4]);
    ctx.strokeStyle = cor;
    ctx.lineWidth = largura || 1;
    ctx.beginPath();
    ctx.moveTo(x, geo.PAD.top);
    ctx.lineTo(x, geo.H - geo.PAD.bottom);
    ctx.stroke();
    ctx.restore();
  }

  /** Faixa de realce entre dois preços (ex.: spot → breakeven). */
  function faixa(ctx, geo, x1, x2) {
    var a = Math.min(x1, x2), b = Math.max(x1, x2);
    ctx.save();
    ctx.fillStyle = CORES.faixa;
    ctx.fillRect(a, geo.PAD.top, b - a, geo.cH);
    ctx.restore();
  }

  /**
   * Aplica o zoom/pan de uma view {zoom, pan} ao intervalo [Smin, Smax]
   * já calculado pela tela — pan em fração do intervalo original, não em
   * preço absoluto, para continuar fazendo sentido em qualquer ativo.
   * Cada tela chama isto logo após calcular Smin/Smax "base" (a partir dos
   * strikes) e antes de gerar a série de pontos da curva.
   */
  function aplicaZoom(Smin, Smax, view) {
    var zoom = (view && view.zoom) || 1;
    var pan  = (view && view.pan)  || 0;
    var largura = (Smax - Smin) / zoom;
    var centro  = (Smin + Smax) / 2 + pan * (Smax - Smin);
    return { Smin: centro - largura / 2, Smax: centro + largura / 2 };
  }

  /**
   * Liga zoom (roda do mouse) e pan (arrastar) num canvas de payoff.
   * `view` é o objeto {zoom, pan} mutável (guardado pela tela, tipicamente
   * em canvas._payoffView); `redesenha` é a função local de desenho da
   * tela (drawChart/draw/…), chamada a cada mudança de view.
   * Não depende de nenhum outro estado — cada tela mantém seu próprio
   * cálculo de payoff intacto, só o range visível muda.
   */
  function ligaZoom(canvas, view, redesenha) {
    if (canvas._payoffZoomCtrl) return canvas._payoffZoomCtrl;
    var arrastando = false, moveu = false, ultimoX = 0;

    canvas.addEventListener('wheel', function (e) {
      e.preventDefault();
      var fator = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      view.zoom = Math.min(Math.max(view.zoom * fator, 1), 30);
      redesenha();
    }, { passive: false });

    canvas.addEventListener('mousedown', function (e) {
      arrastando = true; moveu = false;
      ultimoX = e.clientX;
      canvas.style.cursor = 'grabbing';
    });
    window.addEventListener('mouseup', function () {
      if (arrastando) { arrastando = false; canvas.style.cursor = 'grab'; }
    });
    // Captura na fase de captura (antes de qualquer listener de tooltip
    // adicionado depois): assim o pan sempre ganha prioridade e o tooltip
    // de cada tela só roda quando NÃO se está arrastando o gráfico.
    canvas.addEventListener('mousemove', function (e) {
      if (!arrastando) return;
      moveu = true;
      var dx = e.clientX - ultimoX;
      ultimoX = e.clientX;
      // desloca em fração do intervalo visível, dividido pela largura do
      // canvas em CSS px (não canvas.width, que já vem em px de device)
      var rect = canvas.getBoundingClientRect();
      view.pan -= (dx / rect.width) / view.zoom;
      redesenha();
    }, true);
    canvas.addEventListener('dblclick', function () {
      view.zoom = 1; view.pan = 0;
      redesenha();
    });
    canvas.style.cursor = 'grab';

    canvas._payoffZoomCtrl = {
      estaArrastando: function () { return arrastando && moveu; }
    };
    return canvas._payoffZoomCtrl;
  }

  global.PayoffStyle = {
    CORES: CORES,
    grade: grade,
    eixoZero: eixoZero,
    borda: borda,
    areas: areas,
    curva: curva,
    marco: marco,
    faixa: faixa,
    pilula: pilula,
    aplicaZoom: aplicaZoom,
    ligaZoom: ligaZoom
  };
})(window);

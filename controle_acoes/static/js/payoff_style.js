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
    real:      '#4a7fe0',                    // payoff real (marcado a mercado)
    delta:     '#e05252',                    // curva de delta
    theta:     '#e0a020',                    // curva de theta
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
   * Mesma ideia de aplicaZoom, para o eixo Y (resultado R$) — usa
   * view.zoomY/panY, independentes de zoom/pan (eixo X). Uma view sem
   * zoomY/panY (telas antigas que só chamam aplicaZoom) se comporta como
   * zoomY=1: o range Y passado entra intacto.
   */
  function aplicaZoomY(Ymin, Ymax, view) {
    var zoom = (view && view.zoomY) || 1;
    var pan  = (view && view.panY)  || 0;
    var altura = (Ymax - Ymin) / zoom;
    var centro = (Ymin + Ymax) / 2 + pan * (Ymax - Ymin);
    return { Ymin: centro - altura / 2, Ymax: centro + altura / 2 };
  }

  /**
   * Liga zoom (roda do mouse) e pan (arrastar) num canvas de payoff.
   * `view` é o objeto {zoom, pan, zoomY, panY} mutável (guardado pela tela,
   * tipicamente em canvas._payoffView); `redesenha` é a função local de
   * desenho da tela (drawChart/draw/…), chamada a cada mudança de view.
   * Não depende de nenhum outro estado — cada tela mantém seu próprio
   * cálculo de payoff intacto, só o range visível muda.
   *
   * Eixo X (preço, sempre existiu): roda = zoom, arrastar = pan.
   * Eixo Y (resultado R$, novo): Shift+roda = zoom, Shift+arrastar = pan.
   * Isso deixa o gesto "só roda"/"só arrastar" de sempre intacto (não muda
   * o comportamento de quem já usava o zoom) e adiciona o eixo Y como um
   * modificador — sem precisar de um segundo controle na tela.
   */
  function ligaZoom(canvas, view, redesenha) {
    if (canvas._payoffZoomCtrl) return canvas._payoffZoomCtrl;
    if (view.zoomY == null) view.zoomY = 1;
    if (view.panY  == null) view.panY  = 0;
    var arrastando = false, arrastandoY = false, moveu = false, ultimoX = 0, ultimoY = 0;

    canvas.addEventListener('wheel', function (e) {
      e.preventDefault();
      var fator = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      if (e.shiftKey) {
        view.zoomY = Math.min(Math.max(view.zoomY * fator, 1), 30);
      } else {
        view.zoom = Math.min(Math.max(view.zoom * fator, 1), 30);
      }
      redesenha();
    }, { passive: false });

    canvas.addEventListener('mousedown', function (e) {
      if (e.shiftKey) { arrastandoY = true; ultimoY = e.clientY; }
      else { arrastando = true; ultimoX = e.clientX; }
      moveu = false;
      canvas.style.cursor = 'grabbing';
    });
    window.addEventListener('mouseup', function () {
      if (arrastando || arrastandoY) {
        arrastando = false; arrastandoY = false;
        canvas.style.cursor = 'grab';
      }
    });
    // Captura na fase de captura (antes de qualquer listener de tooltip
    // adicionado depois): assim o pan sempre ganha prioridade e o tooltip
    // de cada tela só roda quando NÃO se está arrastando o gráfico.
    canvas.addEventListener('mousemove', function (e) {
      if (!arrastando && !arrastandoY) return;
      moveu = true;
      var rect = canvas.getBoundingClientRect();
      if (arrastandoY) {
        var dy = e.clientY - ultimoY;
        ultimoY = e.clientY;
        // eixo Y da tela cresce pra baixo; inverte pra "arrastar pra cima" subir o range
        view.panY += (dy / rect.height) / view.zoomY;
      } else {
        var dx = e.clientX - ultimoX;
        ultimoX = e.clientX;
        // desloca em fração do intervalo visível, dividido pela largura do
        // canvas em CSS px (não canvas.width, que já vem em px de device)
        view.pan -= (dx / rect.width) / view.zoom;
      }
      redesenha();
    }, true);
    canvas.addEventListener('dblclick', function () {
      view.zoom = 1; view.pan = 0; view.zoomY = 1; view.panY = 0;
      redesenha();
    });
    canvas.style.cursor = 'grab';

    canvas._payoffZoomCtrl = {
      estaArrastando: function () { return (arrastando || arrastandoY) && moveu; }
    };
    return canvas._payoffZoomCtrl;
  }

  /* ══════════ Curvas teóricas: payoff real, delta e theta ══════════
   *
   * A curva amarela mostra o payoff NO VENCIMENTO (valor intrínseco). Antes
   * dele a estrutura vale outra coisa: há valor de tempo. Estas funções
   * calculam, para uma data escolhida entre hoje e o vencimento:
   *   - payoff real  — marcação a mercado por Black-Scholes naquela data;
   *   - delta        — quanto a estrutura ganha/perde por R$ 1 no ativo;
   *   - theta        — quanto ela perde por dia que passa (R$/dia).
   *
   * As pernas chegam no formato que as telas de estrutura já usam:
   * {type:'CALL'|'PUT'|'STOCK', side:'BUY'|'SELL', qty, strike, premium,
   *  exp:'YYYY-MM-DD', iv} — iv em fração (0,28 = 28%).
   */
  var MS_DIA = 86400000, ANO = 365.25;

  function _normCDF(x) {
    var a = [0.319381530, -0.356563782, 1.781477937, -1.821255978, 1.330274429];
    var L = Math.abs(x), k = 1 / (1 + 0.2316419 * L);
    var w = 1 - (1 / Math.sqrt(2 * Math.PI)) * Math.exp(-L * L / 2) *
            (a[0]*k + a[1]*k*k + a[2]*k*k*k + a[3]*k*k*k*k + a[4]*k*k*k*k*k);
    return x < 0 ? 1 - w : w;
  }
  function _normPDF(x) { return Math.exp(-x * x / 2) / Math.sqrt(2 * Math.PI); }

  function _bs(S, K, T, r, sig, isCall) {
    if (T <= 0 || sig <= 0 || S <= 0 || K <= 0)
      return isCall ? Math.max(0, S - K) : Math.max(0, K - S);
    var sq = Math.sqrt(T);
    var d1 = (Math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * sq), d2 = d1 - sig * sq;
    return isCall ? S * _normCDF(d1) - K * Math.exp(-r * T) * _normCDF(d2)
                  : K * Math.exp(-r * T) * _normCDF(-d2) - S * _normCDF(-d1);
  }
  function _bsDelta(S, K, T, r, sig, isCall) {
    if (T <= 0 || sig <= 0 || S <= 0 || K <= 0)
      return isCall ? (S > K ? 1 : 0) : (S < K ? -1 : 0);
    var d1 = (Math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * Math.sqrt(T));
    return isCall ? _normCDF(d1) : _normCDF(d1) - 1;
  }
  /** Theta por DIA (não por ano) — é assim que a mesa lê o número. */
  function _bsTheta(S, K, T, r, sig, isCall) {
    if (T <= 0 || sig <= 0 || S <= 0 || K <= 0) return 0;
    var sq = Math.sqrt(T);
    var d1 = (Math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * sq), d2 = d1 - sig * sq;
    var t1 = -(S * _normPDF(d1) * sig) / (2 * sq);
    var anual = isCall ? t1 - r * K * Math.exp(-r * T) * _normCDF(d2)
                       : t1 + r * K * Math.exp(-r * T) * _normCDF(-d2);
    return anual / ANO;
  }

  function _diaISO(d) {
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2)
         + '-' + ('0' + d.getDate()).slice(-2);
  }
  function _parseDia(iso) { return new Date(iso + 'T00:00:00'); }
  function _hojeISO() { var h = new Date(); h.setHours(0, 0, 0, 0); return _diaISO(h); }

  /** Vencimentos das pernas de opção, em ordem. */
  function vencimentos(legs) {
    var e = [];
    (legs || []).forEach(function (l) {
      if (l.type !== 'STOCK' && l.exp && e.indexOf(l.exp) < 0) e.push(l.exp);
    });
    return e.sort();
  }

  /**
   * Valor da estrutura a preço S na data `dataStr`, com delta e theta.
   * Perna já vencida nessa data entra pelo intrínseco; perna viva entra por
   * Black-Scholes. Sem iv, cai no intrínseco (sem valor de tempo).
   */
  function teoricoEm(S, legs, dataStr, selicPct) {
    var r = (selicPct || 0) / 100, ref = _parseDia(dataStr);
    var val = 0, delta = 0, theta = 0;
    (legs || []).forEach(function (l) {
      var sign = l.side === 'BUY' ? 1 : -1, q = l.qty || 0;
      if (l.type === 'STOCK') {
        val += sign * q * (S - (l.premium || 0));
        delta += sign * q;
        return;
      }
      if (!(l.strike > 0)) return;
      var isCall = l.type === 'CALL';
      var T = l.exp ? (_parseDia(l.exp) - ref) / (ANO * MS_DIA) : 0;
      var custo = sign * q * (l.premium || 0);     // pago (BUY) / recebido (SELL)
      if (T > 0 && l.iv > 0) {
        val   += sign * q * _bs(S, l.strike, T, r, l.iv, isCall) - custo;
        delta += sign * q * _bsDelta(S, l.strike, T, r, l.iv, isCall);
        theta += sign * q * _bsTheta(S, l.strike, T, r, l.iv, isCall);
      } else {
        var intr = isCall ? Math.max(0, S - l.strike) : Math.max(0, l.strike - S);
        val   += sign * q * intr - custo;
        delta += sign * q * (isCall ? (S > l.strike ? 1 : 0) : (S < l.strike ? -1 : 0));
      }
    });
    return { valor: val, delta: delta, theta: theta };
  }

  /** Série {valor, delta, theta} ao longo de Sarr, para uma data. */
  function serieTeorica(Sarr, legs, dataStr, selicPct) {
    var val = [], del = [], the = [];
    for (var i = 0; i < Sarr.length; i++) {
      var p = teoricoEm(Sarr[i], legs, dataStr, selicPct);
      val.push(p.valor); del.push(p.delta); the.push(p.theta);
    }
    return { valor: val, delta: del, theta: the };
  }

  /**
   * Eixo Y secundário (direita) para as curvas que não estão em R$ de payoff
   * — delta (adimensional) e theta (R$/dia). Desenha os rótulos e devolve o
   * projetor y2Px.
   */
  function eixoDireito(ctx, geo, vMin, vMax, rotulo, cor) {
    if (!(vMax > vMin)) { vMax = (vMax || 0) + 1; vMin = (vMin || 0) - 1; }
    var PAD = geo.PAD, cH = geo.cH, x = geo.W - PAD.right;
    function y2Px(v) { return PAD.top + (1 - (v - vMin) / (vMax - vMin)) * cH; }
    ctx.save();
    ctx.fillStyle = cor || CORES.eixoTxt;
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    for (var i = 0; i <= 4; i++) {
      var v = vMin + (vMax - vMin) * i / 4;
      var txt = Math.abs(v) >= 100 ? v.toFixed(0)
              : (Math.abs(v) >= 1 ? v.toFixed(1) : v.toFixed(2));
      ctx.fillText(txt.replace('.', ','), x + 5, y2Px(v));
    }
    if (rotulo) {
      ctx.textAlign = 'center';
      ctx.font = 'bold 10px sans-serif';
      ctx.fillText(rotulo, x + 20, PAD.top - 12);
    }
    ctx.restore();
    return y2Px;
  }

  /**
   * Controles das curvas teóricas: 3 checkboxes (payoff real / delta /
   * theta) e o slider de data, que vai de hoje até o vencimento mais longo.
   * Monta dentro de `host` uma vez só e chama `onChange()` a cada mudança.
   */
  /* Estilo dos controles, injetado uma vez — evita repetir o mesmo CSS nas
     telas que desenham payoff. */
  function _injetaCss() {
    if (document.getElementById('ps-curvas-css')) return;
    var st = document.createElement('style');
    st.id = 'ps-curvas-css';
    st.textContent =
      '.ps-curvas{display:flex;gap:1rem;align-items:center;flex-wrap:wrap;'
    +   'margin:.1rem 0 .5rem;font-size:.82rem;color:var(--text-secondary);}'
    + '.ps-curvas .ps-chk{display:inline-flex;align-items:center;gap:.35rem;cursor:pointer;'
    +   'white-space:nowrap;margin:0;}'
    + '.ps-curvas .ps-chk input{margin:0;cursor:pointer;}'
    + '.ps-data-wrap{display:inline-flex;align-items:center;gap:.5rem;}'
    + '.ps-data{width:180px;cursor:pointer;accent-color:' + CORES.real + ';}'
    + '.ps-data-lbl{font-variant-numeric:tabular-nums;color:var(--text-primary);'
    +   'min-width:96px;display:inline-block;}';
    document.head.appendChild(st);
  }

  function controleData(host, onChange) {
    if (host._ctrlData) return host._ctrlData;
    _injetaCss();
    host.classList.add('ps-curvas');
    host.innerHTML =
      '<label class="ps-chk"><input type="checkbox" class="ps-c-real"> '
      + '<span style="color:' + CORES.real + '">■</span> Payoff real</label>'
      + '<label class="ps-chk"><input type="checkbox" class="ps-c-delta"> '
      + '<span style="color:' + CORES.delta + '">■</span> Delta</label>'
      + '<label class="ps-chk"><input type="checkbox" class="ps-c-theta"> '
      + '<span style="color:' + CORES.theta + '">■</span> Theta</label>'
      + '<span class="ps-data-wrap" style="display:none;">'
      +   '<input type="range" class="ps-data" min="0" max="1" step="1" value="0" '
      +     'title="Arraste para avançar a data até o vencimento">'
      +   '<span class="ps-data-lbl">—</span>'
      + '</span>';

    var api = {
      host: host,
      cRe: host.querySelector('.ps-c-real'),
      cDe: host.querySelector('.ps-c-delta'),
      cTh: host.querySelector('.ps-c-theta'),
      range: host.querySelector('.ps-data'),
      lbl: host.querySelector('.ps-data-lbl'),
      wrap: host.querySelector('.ps-data-wrap'),
      dias: [],
      ativo: function () { return api.cRe.checked || api.cDe.checked || api.cTh.checked; },
      dataSel: function () { return api.dias[+api.range.value] || api.dias[0] || _hojeISO(); },
      /** Refaz o intervalo de datas a partir dos vencimentos das pernas. */
      sincroniza: function (legs) {
        var exps = vencimentos(legs);
        var fim = exps.length ? exps[exps.length - 1] : null;
        var hoje = _hojeISO(), dias = [];
        if (fim && fim > hoje) {
          for (var d = _parseDia(hoje); _diaISO(d) <= fim; d.setDate(d.getDate() + 1))
            dias.push(_diaISO(d));
        } else {
          dias = [hoje];
        }
        var antes = api.dias[+api.range.value];
        api.dias = dias;
        api.range.max = String(Math.max(dias.length - 1, 0));
        var idx = antes ? dias.indexOf(antes) : -1;
        api.range.value = String(idx >= 0 ? idx : 0);
        api.wrap.style.display = api.ativo() ? '' : 'none';
        api.atualizaRotulo();
      },
      atualizaRotulo: function () {
        var iso = api.dataSel(), p = iso.split('-');
        var dd = p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : iso;
        var falta = Math.max(Math.round((_parseDia(iso) - _parseDia(_hojeISO())) / MS_DIA), 0);
        api.lbl.textContent = dd + ' (' + falta + 'd)';
      }
    };

    [api.cRe, api.cDe, api.cTh].forEach(function (c) {
      c.addEventListener('change', function () {
        api.wrap.style.display = api.ativo() ? '' : 'none';
        onChange();
      });
    });
    api.range.addEventListener('input', function () {
      api.atualizaRotulo();
      onChange();
    });

    host._ctrlData = api;
    return api;
  }

  global.PayoffStyle = {
    CORES: CORES,
    vencimentos: vencimentos,
    teoricoEm: teoricoEm,
    serieTeorica: serieTeorica,
    eixoDireito: eixoDireito,
    controleData: controleData,
    grade: grade,
    eixoZero: eixoZero,
    borda: borda,
    areas: areas,
    curva: curva,
    marco: marco,
    faixa: faixa,
    pilula: pilula,
    aplicaZoom: aplicaZoom,
    aplicaZoomY: aplicaZoomY,
    ligaZoom: ligaZoom
  };
})(window);

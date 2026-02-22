#!/usr/bin/env python3
"""
Controle de Ações — Versão Desktop
===================================
Abre o app Flask em janela nativa (pywebview/Edge WebView2).
Atualiza cotações em background via MT5 (tickers mapeados) e
Yahoo Finance (demais tickers).

Uso:
    python desktop_app.py
ou:
    run_desktop.bat
"""

import sys
import os
import threading
import time
import logging

# ── garante que imports locais funcionem ──────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('desktop')

FLASK_PORT = 5001
FLASK_URL  = f'http://127.0.0.1:{FLASK_PORT}'


# ── inicia Flask ──────────────────────────────────────────────────────────────
def run_flask(app):
    app.run(
        host='127.0.0.1',
        port=FLASK_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def wait_for_flask(timeout=15):
    """Aguarda o Flask responder antes de abrir a janela."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(FLASK_URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def init_desktop_settings(app):
    """Força o modo 'mt5' nas Settings do banco para a sessão desktop."""
    with app.app_context():
        from models import db, Settings
        s = Settings.query.filter_by(key='quote_mode').first()
        if s is None:
            s = Settings(key='quote_mode', value='mt5')
            db.session.add(s)
        else:
            s.value = 'mt5'
        db.session.commit()
    logger.info("Configuração: modo MT5 ativado")


# ── ponto de entrada ──────────────────────────────────────────────────────────
def main():
    try:
        import webview
    except Exception as e:
        import traceback
        print("\n=== ERRO ao importar pywebview ===")
        traceback.print_exc()
        print(f"\nDetalhes: {e}")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    # Importa o app Flask
    from app import app as flask_app

    # 1. Inicia Flask em thread daemon
    flask_thread = threading.Thread(target=run_flask, args=(flask_app,), daemon=True)
    flask_thread.start()
    logger.info(f"Flask iniciando em {FLASK_URL} ...")

    # 2. Aguarda Flask estar pronto
    if not wait_for_flask():
        logger.error("Flask não respondeu a tempo. Encerrando.")
        sys.exit(1)
    logger.info("Flask pronto.")

    # 3. Configura modo MT5 no banco
    init_desktop_settings(flask_app)

    # 4. Inicia atualizador de cotações em background
    from mt5_live import start_updater
    start_updater(flask_app)

    # 5. Abre janela desktop
    logger.info("Abrindo janela desktop...")
    window = webview.create_window(
        title='Controle de Ações',
        url=FLASK_URL,
        width=1440,
        height=900,
        resizable=True,
        min_size=(900, 600),
    )
    webview.start(debug=False)
    logger.info("Janela fechada. Encerrando.")


if __name__ == '__main__':
    main()

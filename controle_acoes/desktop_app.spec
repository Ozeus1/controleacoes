# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para o Controle de Ações - Desktop
Gera:  dist\ControleAcoes\ControleAcoes.exe  (pasta, não arquivo único)
Build: build_desktop.bat
"""

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# Coleta automática de pacotes que têm hooks especiais
flask_data,     flask_bin,     flask_hi     = collect_all('flask')
jinja_data,     jinja_bin,     jinja_hi     = collect_all('jinja2')
webview_data,   webview_bin,   webview_hi   = collect_all('webview')
sqlalchemy_data, sqlalchemy_bin, sqlalchemy_hi = collect_all('sqlalchemy')
yfinance_data,  yfinance_bin,  yfinance_hi  = collect_all('yfinance')

a = Analysis(
    ['desktop_app.py'],
    pathex=['.'],
    binaries=(
        flask_bin + jinja_bin + webview_bin + sqlalchemy_bin + yfinance_bin
    ),
    datas=(
        # Arquivos do projeto
        [('templates', 'templates'),
         ('static',    'static'),
         ('.env',      '.')]
        +
        # Pacotes com dados (hooks automáticos)
        flask_data + jinja_data + webview_data + sqlalchemy_data + yfinance_data
    ),
    hiddenimports=(
        # App local
        ['app', 'models', 'services', 'mt5_live']
        +
        # Flask ecosystem
        ['flask', 'flask_login', 'flask_sqlalchemy',
         'werkzeug', 'werkzeug.routing', 'werkzeug.serving',
         'werkzeug.middleware.proxy_fix', 'click']
        +
        # SQLAlchemy / SQLite
        ['sqlalchemy', 'sqlalchemy.dialects.sqlite',
         'sqlalchemy.dialects.sqlite.pysqlite',
         'sqlalchemy.sql.default_comparator']
        +
        # Jinja2
        ['jinja2', 'jinja2.ext', 'jinja2.filters', 'markupsafe']
        +
        # pywebview
        ['webview', 'webview.platforms.winforms',
         'clr_loader', 'pythonnet']
        +
        # MetaTrader5 (opcional — sem erro se não instalado)
        ['MetaTrader5']
        +
        # yfinance e dependências
        ['yfinance', 'pandas', 'numpy', 'requests',
         'multitasking', 'lxml', 'bs4', 'html5lib',
         'appdirs', 'platformdirs', 'frozendict',
         'peewee', 'curl_cffi']
        +
        # Outros
        ['dotenv', 'python_dotenv', 'pytz',
         'zoneinfo', 'dateutil',
         'cryptography', 'cryptography.fernet',
         'cryptography.hazmat.primitives',
         'cryptography.hazmat.backends',
         'cryptography.hazmat.backends.openssl',
         'email', 'email.mime', 'email.mime.text',
         'wsgiref', 'wsgiref.simple_server',
         'http', 'http.server', 'http.client',
         'urllib', 'urllib.parse', 'urllib.request']
        +
        flask_hi + jinja_hi + webview_hi + sqlalchemy_hi + yfinance_hi
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclui pacotes desnecessários para reduzir tamanho
        'tkinter', 'test', 'unittest',
        'pydoc', 'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ControleAcoes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX pode causar falsos positivos em antivírus
    console=True,            # Mantém console para ver logs do MT5/Yahoo
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # Adicione um .ico aqui se quiser ícone personalizado
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ControleAcoes',
)

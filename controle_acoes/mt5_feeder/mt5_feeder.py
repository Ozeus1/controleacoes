"""
mt5_feeder.py
=============
Script local com interface gráfica (Windows) que lê cotações do MetaTrader 5
e envia periodicamente ao site.

Funcionalidades:
  - Carregar config.py via seleção de arquivo
  - Editar TICKER_MAP e OPTION_MAP diretamente na interface
  - Salvar configuração em config.py
  - Iniciar / Parar o envio de cotações
  - Log em tempo real na janela

Requisitos:
    pip install requests MetaTrader5
    (tkinter já vem com Python)
"""

import sys
import os
import time
import threading
import importlib.util
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


# ── Configuração padrão ───────────────────────────────────────────────────────

DEFAULT_CFG = {
    "API_URL": "https://www.invest.casatemporadaceara.cloud/api/update_quotes",
    "API_KEY": "chave_mtq5_2026",
    "USER_ID": 1,
    "INTERVALO_SEGUNDOS": 30,
    "TICKER_MAP": {},
    "OPTION_MAP": {},
}


# ── MT5 helpers ───────────────────────────────────────────────────────────────

def conectar_mt5(log_fn):
    if not MT5_AVAILABLE:
        log_fn("[ERRO] MetaTrader5 não instalado.")
        return False
    if not mt5.initialize():
        log_fn(f"[MT5] Falha ao inicializar: {mt5.last_error()}")
        return False
    info = mt5.terminal_info()
    if info is None:
        log_fn("[MT5] Terminal não encontrado. Abra o MT5 primeiro.")
        return False
    log_fn(f"[MT5] Conectado: {info.name} | build {info.build}")
    return True


def _get_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        mt5.symbol_select(symbol, True)
        for _ in range(3):
            time.sleep(0.5)
            tick = mt5.symbol_info_tick(symbol)
            if tick is not None:
                break
    if tick is None:
        return None, None
    price = tick.last if tick.last > 0 else tick.bid
    if price <= 0:
        return None, None
    info = mt5.symbol_info(symbol)
    change_pct = 0.0
    if info and info.session_open > 0:
        change_pct = round((price - info.session_open) / info.session_open * 100, 2)
    return round(price, 2), change_pct


def obter_cotacoes(ticker_map, log_fn):
    quotes, changes = {}, {}
    log_fn("  [Ativos]")
    for ticker_site, simbolo_mt5 in ticker_map.items():
        price, change = _get_price(simbolo_mt5)
        if price:
            quotes[ticker_site]  = price
            changes[ticker_site] = change
            log_fn(f"    {ticker_site:<12} ({simbolo_mt5:<15}) = R$ {price:.2f}  ({change:+.2f}%)")
        else:
            log_fn(f"    {ticker_site:<12} ({simbolo_mt5:<15}) = sem preço")
    return quotes, changes


def obter_cotacoes_opcoes(option_map, log_fn):
    if not option_map:
        return {}
    for sym in option_map.values():
        if mt5.symbol_info(sym) is None:
            mt5.symbol_select(sym, True)
    time.sleep(1.0)
    options = {}
    log_fn("  [Opções]")
    for ticker_site, simbolo_mt5 in option_map.items():
        price, _ = _get_price(simbolo_mt5)
        if price is not None:
            options[ticker_site] = price
            log_fn(f"    {ticker_site:<12} ({simbolo_mt5:<15}) = R$ {price:.2f}")
        else:
            info = mt5.symbol_info(simbolo_mt5)
            motivo = "não encontrado" if info is None else "preço indisponível"
            log_fn(f"    {ticker_site:<12} ({simbolo_mt5:<15}) = sem preço ({motivo})")
    return options


def enviar_cotacoes(cfg, quotes, changes, options, log_fn):
    if not quotes and not options:
        log_fn("[API] Nada para enviar.")
        return False
    payload = {
        "user_id": cfg["USER_ID"],
        "quotes":  quotes,
        "changes": changes,
        "options": options,
    }
    headers = {"X-API-Key": cfg["API_KEY"], "Content-Type": "application/json"}
    try:
        resp = requests.post(cfg["API_URL"], json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_fn(f"[API] ✓ Ativos: {data.get('updated_assets',[])}  |  Opções: {data.get('updated_options',[])}")
            nfa = data.get('not_found_assets', [])
            nfo = data.get('not_found_options', [])
            if nfa: log_fn(f"[API] ⚠ Não encontrados (ativos): {nfa}")
            if nfo: log_fn(f"[API] ⚠ Não encontrados (opções): {nfo}")
            return True
        elif resp.status_code == 401:
            log_fn("[API] ✗ 401 Não autorizado — verifique API_KEY")
        else:
            log_fn(f"[API] ✗ Erro {resp.status_code}: {resp.text[:200]}")
    except requests.exceptions.ConnectionError:
        log_fn("[API] ✗ Sem conexão com o site.")
    except requests.exceptions.Timeout:
        log_fn("[API] ✗ Timeout.")
    except Exception as e:
        log_fn(f"[API] ✗ {e}")
    return False


# ── Parser de config.py ───────────────────────────────────────────────────────

def load_config_from_file(path):
    """Carrega config.py e retorna dict com os valores."""
    spec = importlib.util.spec_from_file_location("_cfg_loaded", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = dict(DEFAULT_CFG)
    for key in ("API_URL", "API_KEY", "USER_ID", "INTERVALO_SEGUNDOS", "TICKER_MAP", "OPTION_MAP"):
        if hasattr(mod, key):
            cfg[key] = getattr(mod, key)
    return cfg


def save_config_to_file(path, cfg):
    """Salva dict de configuração como config.py."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f'# config.py — salvo em {datetime.now().strftime("%d/%m/%Y %H:%M")}\n\n')
        f.write(f'API_URL = "{cfg["API_URL"]}"\n')
        f.write(f'API_KEY = "{cfg["API_KEY"]}"\n')
        f.write(f'USER_ID = {cfg["USER_ID"]}\n')
        f.write(f'INTERVALO_SEGUNDOS = {cfg["INTERVALO_SEGUNDOS"]}\n\n')
        f.write("TICKER_MAP = {\n")
        for k, v in sorted(cfg["TICKER_MAP"].items()):
            f.write(f'    "{k}": "{v}",\n')
        f.write("}\n\n")
        f.write("OPTION_MAP = {\n")
        for k, v in sorted(cfg["OPTION_MAP"].items()):
            f.write(f'    "{k}": "{v}",\n')
        f.write("}\n")


def parse_map_text(text):
    """Converte texto editável (uma entrada por linha: TICKER,SIMBOLO) em dict."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip().lstrip('"').rstrip(",")
        if not line or line.startswith("#"):
            continue
        # Aceita formatos: "TICK": "SYM"  ou  TICK,SYM  ou  TICK
        if '":"' in line or '": "' in line:
            parts = line.replace('"', "").split(":")
            if len(parts) >= 2:
                k = parts[0].strip().rstrip(",")
                v = parts[1].strip().rstrip(",")
                if k:
                    result[k] = v or k
        elif "," in line:
            parts = line.split(",", 1)
            k = parts[0].strip().strip('"')
            v = parts[1].strip().strip('"') if len(parts) > 1 else k
            if k:
                result[k] = v or k
        else:
            k = line.strip().strip('"')
            if k:
                result[k] = k
    return result


def map_to_text(d):
    """Converte dict em texto editável."""
    return "\n".join(f'"{k}": "{v}",' for k, v in sorted(d.items()))


# ── Interface Gráfica ─────────────────────────────────────────────────────────

class MT5FeederApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MT5 Feeder — Controle de Investimentos")
        self.root.geometry("900x700")
        self.root.minsize(750, 550)

        self.cfg = dict(DEFAULT_CFG)
        self.cfg_path = tk.StringVar(value="")
        self._running = False
        self._thread  = None
        self._stop_event = threading.Event()

        self._build_ui()
        self._try_load_default_config()

    # ── Tenta carregar config.py da mesma pasta do executável ─────────────────
    def _try_load_default_config(self):
        base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__)
        candidate = os.path.join(base, "config.py")
        if os.path.exists(candidate):
            try:
                self.cfg = load_config_from_file(candidate)
                self.cfg_path.set(candidate)
                self._cfg_to_ui()
                self._log(f"[INFO] config.py carregado automaticamente: {candidate}")
            except Exception as e:
                self._log(f"[AVISO] Não foi possível carregar config.py automático: {e}")

    # ── Construção da UI ──────────────────────────────────────────────────────
    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Aba 1: Configuração ──
        tab_cfg = ttk.Frame(nb)
        nb.add(tab_cfg, text="  ⚙ Configuração  ")
        self._build_tab_config(tab_cfg)

        # ── Aba 2: Ticker Map ──
        tab_tickers = ttk.Frame(nb)
        nb.add(tab_tickers, text="  📋 TICKER_MAP  ")
        self._build_tab_map(tab_tickers, "ticker")

        # ── Aba 3: Option Map ──
        tab_options = ttk.Frame(nb)
        nb.add(tab_options, text="  📊 OPTION_MAP  ")
        self._build_tab_map(tab_options, "option")

        # ── Aba 4: Log / Execução ──
        tab_run = ttk.Frame(nb)
        nb.add(tab_run, text="  ▶ Executar  ")
        self._build_tab_run(tab_run)

    def _build_tab_config(self, parent):
        pad = {"padx": 10, "pady": 4}

        # Arquivo config.py
        frm_file = ttk.LabelFrame(parent, text="Arquivo config.py", padding=8)
        frm_file.pack(fill="x", padx=10, pady=(10, 4))

        ttk.Entry(frm_file, textvariable=self.cfg_path, state="readonly",
                  width=60).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(frm_file, text="📂 Carregar...", command=self._browse_config).pack(side="left", padx=2)
        ttk.Button(frm_file, text="💾 Salvar", command=self._save_config).pack(side="left", padx=2)
        ttk.Button(frm_file, text="💾 Salvar Como...", command=self._save_config_as).pack(side="left", padx=2)

        # Parâmetros
        frm_params = ttk.LabelFrame(parent, text="Parâmetros de conexão", padding=8)
        frm_params.pack(fill="x", padx=10, pady=4)

        fields = [
            ("API URL:", "api_url", 60),
            ("API Key:", "api_key", 40),
            ("User ID:", "user_id", 10),
            ("Intervalo (seg):", "intervalo", 10),
        ]
        self._entries = {}
        for i, (lbl, key, w) in enumerate(fields):
            ttk.Label(frm_params, text=lbl, width=16, anchor="e").grid(row=i, column=0, **pad, sticky="e")
            e = ttk.Entry(frm_params, width=w)
            e.grid(row=i, column=1, **pad, sticky="w")
            self._entries[key] = e

        # Preenche com valores padrão
        self._entries["api_url"].insert(0, self.cfg["API_URL"])
        self._entries["api_key"].insert(0, self.cfg["API_KEY"])
        self._entries["user_id"].insert(0, str(self.cfg["USER_ID"]))
        self._entries["intervalo"].insert(0, str(self.cfg["INTERVALO_SEGUNDOS"]))

    def _build_tab_map(self, parent, kind):
        hint = ('Um ticker por linha. Formatos aceitos:\n'
                '  "PETR4": "PETR4",   ou   PETR4,PETR4   ou   PETR4')
        ttk.Label(parent, text=hint, foreground="gray").pack(anchor="w", padx=10, pady=(8, 2))

        txt = scrolledtext.ScrolledText(parent, font=("Consolas", 10), wrap="none")
        txt.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        btn_frm = ttk.Frame(parent)
        btn_frm.pack(fill="x", padx=10, pady=(0, 8))
        map_key = "TICKER_MAP" if kind == "ticker" else "OPTION_MAP"
        ttk.Button(btn_frm, text="✔ Aplicar",
                   command=lambda: self._apply_map(kind, txt)).pack(side="left", padx=4)
        ttk.Button(btn_frm, text="🗑 Limpar",
                   command=lambda: txt.delete("1.0", "end")).pack(side="left", padx=4)

        if kind == "ticker":
            self._txt_ticker = txt
        else:
            self._txt_option = txt

        # Preenche com valores atuais
        txt.insert("1.0", map_to_text(self.cfg.get(map_key, {})))

    def _build_tab_run(self, parent):
        btn_frm = ttk.Frame(parent)
        btn_frm.pack(fill="x", padx=10, pady=8)

        self._btn_start = ttk.Button(btn_frm, text="▶  Iniciar", command=self._start,
                                     style="Accent.TButton")
        self._btn_start.pack(side="left", padx=4)

        self._btn_stop = ttk.Button(btn_frm, text="⏹  Parar", command=self._stop,
                                    state="disabled")
        self._btn_stop.pack(side="left", padx=4)

        self._status_var = tk.StringVar(value="● Parado")
        ttk.Label(btn_frm, textvariable=self._status_var, width=20).pack(side="left", padx=12)

        self._log_box = scrolledtext.ScrolledText(parent, font=("Consolas", 9),
                                                   wrap="word", state="disabled",
                                                   background="#0f172a", foreground="#94a3b8")
        self._log_box.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._log_box.tag_config("ok",   foreground="#10b981")
        self._log_box.tag_config("warn", foreground="#f59e0b")
        self._log_box.tag_config("err",  foreground="#ef4444")
        self._log_box.tag_config("info", foreground="#94a3b8")

    # ── Helpers da UI ─────────────────────────────────────────────────────────
    def _log(self, msg):
        """Escreve mensagem no log — seguro para chamar de outra thread."""
        def _write():
            self._log_box.config(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            line = f"[{ts}] {msg}\n"
            tag = "ok" if "✓" in msg else "err" if ("✗" in msg or "ERRO" in msg or "Falha" in msg) else \
                  "warn" if "⚠" in msg or "AVISO" in msg else "info"
            self._log_box.insert("end", line, tag)
            self._log_box.see("end")
            self._log_box.config(state="disabled")
        self.root.after(0, _write)

    def _cfg_to_ui(self):
        """Popula os campos da UI a partir de self.cfg."""
        for key, widget in self._entries.items():
            widget.delete(0, "end")
        self._entries["api_url"].insert(0, self.cfg.get("API_URL", ""))
        self._entries["api_key"].insert(0, self.cfg.get("API_KEY", ""))
        self._entries["user_id"].insert(0, str(self.cfg.get("USER_ID", 1)))
        self._entries["intervalo"].insert(0, str(self.cfg.get("INTERVALO_SEGUNDOS", 30)))

        self._txt_ticker.delete("1.0", "end")
        self._txt_ticker.insert("1.0", map_to_text(self.cfg.get("TICKER_MAP", {})))

        self._txt_option.delete("1.0", "end")
        self._txt_option.insert("1.0", map_to_text(self.cfg.get("OPTION_MAP", {})))

    def _ui_to_cfg(self):
        """Lê campos da UI e atualiza self.cfg."""
        self.cfg["API_URL"]             = self._entries["api_url"].get().strip()
        self.cfg["API_KEY"]             = self._entries["api_key"].get().strip()
        self.cfg["USER_ID"]             = int(self._entries["user_id"].get().strip() or 1)
        self.cfg["INTERVALO_SEGUNDOS"]  = int(self._entries["intervalo"].get().strip() or 30)
        self.cfg["TICKER_MAP"]          = parse_map_text(self._txt_ticker.get("1.0", "end"))
        self.cfg["OPTION_MAP"]          = parse_map_text(self._txt_option.get("1.0", "end"))

    def _apply_map(self, kind, txt):
        text = txt.get("1.0", "end")
        parsed = parse_map_text(text)
        txt.delete("1.0", "end")
        txt.insert("1.0", map_to_text(parsed))
        key = "TICKER_MAP" if kind == "ticker" else "OPTION_MAP"
        self.cfg[key] = parsed
        messagebox.showinfo("Aplicado", f"{key}: {len(parsed)} entradas.")

    # ── Arquivo ───────────────────────────────────────────────────────────────
    def _browse_config(self):
        path = filedialog.askopenfilename(
            title="Selecionar config.py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.cfg = load_config_from_file(path)
            self.cfg_path.set(path)
            self._cfg_to_ui()
            self._log(f"[INFO] Carregado: {path}")
            messagebox.showinfo("Carregado", f"config.py carregado com sucesso!\n\n"
                                f"Ativos: {len(self.cfg['TICKER_MAP'])} | "
                                f"Opções: {len(self.cfg['OPTION_MAP'])}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar config.py:\n{e}")

    def _save_config(self):
        path = self.cfg_path.get()
        if not path:
            self._save_config_as()
            return
        self._ui_to_cfg()
        try:
            save_config_to_file(path, self.cfg)
            self._log(f"[INFO] Salvo: {path}")
            messagebox.showinfo("Salvo", "config.py salvo com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

    def _save_config_as(self):
        path = filedialog.asksaveasfilename(
            title="Salvar config.py",
            defaultextension=".py",
            initialfile="config.py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if not path:
            return
        self._ui_to_cfg()
        try:
            save_config_to_file(path, self.cfg)
            self.cfg_path.set(path)
            self._log(f"[INFO] Salvo como: {path}")
            messagebox.showinfo("Salvo", f"config.py salvo em:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

    # ── Execução ──────────────────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return
        self._ui_to_cfg()

        if not self.cfg["TICKER_MAP"] and not self.cfg["OPTION_MAP"]:
            messagebox.showwarning("Atenção", "TICKER_MAP e OPTION_MAP estão vazios.\n"
                                   "Carregue um config.py ou edite os mapas antes de iniciar.")
            return

        if not MT5_AVAILABLE:
            messagebox.showerror("Erro", "MetaTrader5 não está instalado.\n"
                                  "Execute: pip install MetaTrader5")
            return

        self._running = True
        self._stop_event.clear()
        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal")
        self._status_var.set("● Rodando")

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _stop(self):
        self._running = False
        self._stop_event.set()
        self._btn_start.config(state="normal")
        self._btn_stop.config(state="disabled")
        self._status_var.set("● Parando...")
        self._log("[INFO] Pedido de parada enviado...")

    def _loop(self):
        self._log("=" * 50)
        self._log("  MT5 Feeder iniciado")
        self._log(f"  URL      : {self.cfg['API_URL']}")
        self._log(f"  Ativos   : {len(self.cfg['TICKER_MAP'])}")
        self._log(f"  Opções   : {len(self.cfg['OPTION_MAP'])}")
        self._log(f"  Intervalo: {self.cfg['INTERVALO_SEGUNDOS']}s")
        self._log("=" * 50)

        if not conectar_mt5(self._log):
            self.root.after(0, self._stop)
            self._status_var.set("● Erro MT5")
            return

        sem_conexao = 0
        while self._running and not self._stop_event.is_set():
            self._log(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Lendo MT5...")

            if not mt5.terminal_info():
                sem_conexao += 1
                self._log(f"[MT5] Desconectado. Tentando reconectar ({sem_conexao})...")
                if not conectar_mt5(self._log):
                    self._stop_event.wait(self.cfg["INTERVALO_SEGUNDOS"])
                    continue
                sem_conexao = 0

            quotes, changes = obter_cotacoes(self.cfg["TICKER_MAP"], self._log)
            options = obter_cotacoes_opcoes(self.cfg["OPTION_MAP"], self._log)
            enviar_cotacoes(self.cfg, quotes, changes, options, self._log)

            self._log(f"  Próxima em {self.cfg['INTERVALO_SEGUNDOS']}s...")
            self._stop_event.wait(self.cfg["INTERVALO_SEGUNDOS"])

        mt5.shutdown()
        self._log("[MT5] Desconectado.")
        self._log("[INFO] Feeder parado.")
        self.root.after(0, lambda: self._status_var.set("● Parado"))
        self.root.after(0, lambda: self._btn_start.config(state="normal"))
        self.root.after(0, lambda: self._btn_stop.config(state="disabled"))


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    try:
        # Ícone (ignora se não existir)
        ico = os.path.join(os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__),
                           "icon.ico")
        if os.path.exists(ico):
            root.iconbitmap(ico)
    except Exception:
        pass

    MT5FeederApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

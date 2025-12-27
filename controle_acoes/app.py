
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from models import db, Asset, Settings, User, TradeHistory, Option, FixedIncome, InvestmentFund, Crypto, Pension, International
from services import get_quotes, get_raw_quote_data
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo
# yfinance removed to avoid dependency hell on VPS

# Load env vars
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default_secret')

# --- Custom Filters ---
@app.template_filter('brl')
def format_brl(value):
    if value is None:
        return 'R$ 0,00'
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

@app.template_filter('pct')
def format_pct(value):
    if value is None:
        return '0,00%'
    return f"{value:,.2f}%".replace('.', ',')


basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

db_path = os.path.join(instance_path, 'investments.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def brl_fmt(value):
    if value is None:
        return ""
    return "{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")

app.jinja_env.filters['brl_fmt'] = brl_fmt

db.init_app(app)


# --- Options Module Routes ---

@app.route('/opcoes')
@login_required
def opcoes():
    options = Option.query.all()
    
    # Process options to add calculated fields and fetch underlying quotes
    processed_options = []
    
    # Get list of unique underlyings to fetch quotes
    underlyings = list(set([o.underlying_asset for o in options]))
    quotes = get_quotes(underlyings) if underlyings else {}
    
    for opt in options:
        underlying_price = 0.0
        if opt.underlying_asset in quotes:
            underlying_price = quotes[opt.underlying_asset].get('price', 0.0)
            
        total_sold = opt.quantity * opt.sale_price
        
        # Profit for SHORT position: (Sale Price - Current Price) * Qty
        # If Current Price is 0 (not updated), assume profit is full sale price? No, assume 0 cost effectively?
        # Let's use the manual current_option_price.
        current_val = opt.quantity * opt.current_option_price
        profit = total_sold - current_val
        profit_pct = (profit / total_sold * 100) if total_sold > 0 else 0
        
        processed_options.append({
            'option': opt,
            'underlying_price': underlying_price,
            'total_sold': total_sold,
            'profit': profit,
            'profit_pct': profit_pct
        })
        
    return render_template('opcoes.html', options=processed_options)

@app.route('/add_option', methods=['GET', 'POST'])
@login_required
def add_option():
    # Similar to add_asset
    if request.method == 'POST':
        ticker = request.form.get('ticker').upper()
        quantity = int(request.form.get('quantity'))
        underlying = request.form.get('underlying_asset').upper()
        strike = float(request.form.get('strike_price').replace(',', '.'))
        expiration = datetime.strptime(request.form.get('expiration_date'), '%Y-%m-%d').date()
        sale_price = float(request.form.get('sale_price').replace(',', '.'))
        
        # Current price (optional on add)
        curr_price_str = request.form.get('current_option_price')
        current_option_price = float(curr_price_str.replace(',', '.')) if curr_price_str else 0.0
        
        opt = Option(
            ticker=ticker,
            quantity=quantity,
            underlying_asset=underlying,
            strike_price=strike,
            expiration_date=expiration,
            sale_price=sale_price,
            current_option_price=current_option_price
        )
        db.session.add(opt)
        db.session.commit()
        
        flash("Opção adicionada com sucesso!")
        return redirect(url_for('opcoes'))
        
    return render_template('add_option.html')

@app.route('/edit_option/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_option(id):
    opt = Option.query.get_or_404(id)
    if request.method == 'POST':
        opt.ticker = request.form.get('ticker').upper()
        opt.quantity = int(request.form.get('quantity'))
        opt.underlying_asset = request.form.get('underlying_asset').upper()
        opt.strike_price = float(request.form.get('strike_price').replace(',', '.'))
        opt.expiration_date = datetime.strptime(request.form.get('expiration_date'), '%Y-%m-%d').date()
        opt.sale_price = float(request.form.get('sale_price').replace(',', '.'))
        
        curr_price_str = request.form.get('current_option_price')
        if curr_price_str:
            opt.current_option_price = float(curr_price_str.replace(',', '.'))
            
        db.session.commit()
        return redirect(url_for('opcoes'))
        
    return render_template('add_option.html', option=opt, edit=True)

@app.route('/delete_option/<int:id>')
@login_required
def delete_option(id):
    opt = Option.query.get_or_404(id)
    db.session.delete(opt)
    db.session.commit()
    return redirect(url_for('opcoes'))

@app.route('/update_options_quotes', methods=['POST'])
@login_required
def update_options_quotes():
    # Only updates basic info not stored in DB currently (since we fetch on load),
    # but could be used if we stored underlying price.
    # For now, just reload the page as the page logic fetches fresh data.
    # We could force a refresh or flash message.
    flash("Cotações dos ativos subjacentes atualizadas na visualização.")
    return redirect(url_for('opcoes'))

@app.route('/close_option/<int:id>', methods=['GET', 'POST'])
@login_required
def close_option(id):
    opt = Option.query.get_or_404(id)
    
    # If using a separate template for closing, we'd render it.
    # For simplicity, if GET, maybe show a confirmation or small form?
    # User requested "Gravar saída (nas saídas gravar os lucros e prejuízos em tabela a parte na página histórico)".
    # Let's reuse exit.html or make a simple one. Reusing logic implies we need a form for "Exit Price" (Buy Back Price).
    
    if request.method == 'POST':
        buy_back_price = float(request.form.get('price').replace(',', '.'))
        date_exit = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        
        # Profit Calculation for SHORT
        # Profit = (Sale Price - Buy Back Price) * Qty
        profit_val = (opt.sale_price - buy_back_price) * opt.quantity
        profit_pct = (profit_val / (opt.quantity * opt.sale_price) * 100) if opt.sale_price > 0 else 0
        
        history = TradeHistory(
            ticker=opt.ticker,
            strategy="OPCAO",
            entry_date=None, # We don't track entry date on Option model currently? We could add it or ignore.
            exit_date=date_exit,
            buy_price=buy_back_price, # Price we paid to close
            sell_price=opt.sale_price, # Price we sold at start
            quantity=opt.quantity,
            profit_value=profit_val,
            profit_pct=profit_pct,
            days_held=0, # Unknown entry date
            reason="ENCERRAMENTO"
        )
        db.session.add(history)
        db.session.delete(opt) # Remove from active options
        db.session.commit()
        
        flash("Saída de opção registrada no histórico!")
        return redirect(url_for('opcoes'))
        
    # Render a simple exit form for option
    return render_template('close_option.html', option=opt, today=date.today())


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        # In a multi-worker environment (Gunicorn), multiple workers might try to create tables simultaneously.
        # If one succeeds, the others might fail with "table already exists".
        # We catch this to allow the server to start.
        print(f"Database initialization note: {e}")

@app.route('/')
@login_required
def index():
    return redirect(url_for('acoes'))

@app.route('/acoes')
@login_required
def acoes():
    # Filter: Type ACAO, Strategy HOLDER
    assets = Asset.query.filter_by(type='ACAO', strategy='HOLDER').all()
    # Can reuse logic or make a helper function for processing
    processed_assets = process_assets(assets)
    return render_template('acoes.html', assets=processed_assets)

@app.route('/fiis')
@login_required
def fiis():
    # Filter: Type FII, Strategy HOLDER
    assets = Asset.query.filter_by(type='FII', strategy='HOLDER').all()
    processed_assets = process_assets(assets)
    return render_template('fiis.html', assets=processed_assets)

@app.route('/swingtrade')
@login_required
def swingtrade():
    # Filter: Strategy SWING (Type can be any, usually ACAO)
    assets = Asset.query.filter_by(strategy='SWING').all()
    processed_assets = process_assets(assets) 
    return render_template('swingtrade.html', assets=processed_assets)

def process_assets(assets):
    if not assets:
        return []
    
    # Calculate total value for weighting
    total_value_list = 0
    
    # Pre-calc totals
    for a in assets:
        # Use stored price if available, else 0 or avg_price
        price = a.current_price if a.current_price else 0.0
        total_value_list += (a.quantity * price)
        
    final_data = []
    
    for a in assets:
        # Use stored data
        current_price = a.current_price if a.current_price else 0.0
        change_desc = f"{a.daily_change:.2f}%" if a.daily_change else "0.00%"
        
        total_invested = a.quantity * a.avg_price
        current_total = a.quantity * current_price
        
        profit = current_total - total_invested
        profit_pct = (profit / total_invested * 100) if total_invested > 0 else 0
        
        weight = (current_total / total_value_list * 100) if total_value_list > 0 else 0
        
        # Day Gain Calculation
        if a.daily_change and current_price > 0:
            # prev_close = price / (1 + pct/100)
            prev_close = current_price / (1 + (a.daily_change/100))
            day_gain = a.quantity * (current_price - prev_close)
        else:
            day_gain = 0.0

        final_data.append({
            'asset': a,
            'current_price': current_price,
            'change_percent': a.daily_change,
            'total_invested': total_invested,
            'current_total': current_total,
            'profit': profit,
            'profit_pct': profit_pct,
            'day_gain': day_gain,
            'weight': weight,
            'last_update': a.last_update.strftime('%d/%m %H:%M') if a.last_update else '-'
        })
        
    return final_data

def update_all_assets_logic():
    with app.app_context():
        assets = Asset.query.all()
        # Sequential update: 1 request per asset
        token = Settings.get_value('brapi_token')
        
        for asset in assets:
            try:
                # Fetch individually (simulating "one line at a time")
                # We could optimize by fetching batch of 1? 
                # get_quotes supports list, let's pass single list.
                quotes = get_quotes([asset.ticker])
                if asset.ticker in quotes:
                    q = quotes[asset.ticker]
                    asset.current_price = q.get('price', 0.0)
                    asset.daily_change = q.get('change_percent', 0.0)
                    # Correct Timezone: UTC-3 (Sao Paulo)
                    asset.last_update = datetime.now(ZoneInfo('America/Sao_Paulo'))
                    db.session.commit() # Commit per line? User said "update one line at a time"
                    # Maybe not commit db per line but update API per line.
                    # Let's commit every few or at end. But to be safe committed per line.
            except Exception as e:
                print(f"Error updating {asset.ticker}: {e}")
            # time.sleep(1) # Uncomment if strict rate limit needed
            
@app.route('/update_quotes', methods=['POST'])
@login_required
def update_quotes():
    # Run synchronously (might slow down req)
    update_all_assets_logic()
    flash("Cotações atualizadas com sucesso!")
    return redirect(request.referrer or url_for('index'))


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    if request.method == 'POST':
        ticker = request.form.get('ticker').upper()
        type_ = request.form.get('type')
        strategy = request.form.get('strategy', 'HOLDER')
        qty = int(request.form.get('quantity'))
        price = float(request.form.get('price').replace(',', '.'))
        
        # New fields
        stop_loss = request.form.get('stop_loss')
        gain1 = request.form.get('gain1')
        gain2 = request.form.get('gain2')
        recommendation = request.form.get('recommendation')
        fii_type = request.form.get('fii_type')
        
        stop_loss = float(stop_loss.replace(',', '.')) if stop_loss else None
        gain1 = float(gain1.replace(',', '.')) if gain1 else None
        gain2 = float(gain2.replace(',', '.')) if gain2 else None

        # Entry Date (default to today if missing)
        # Assuming form doesn't have it yet, set default. User can edit later or we add field.
        recommendation = request.form.get('recommendation')
        fii_type = request.form.get('fii_type')
        sector = request.form.get('sector')
        
        stop_loss = float(stop_loss.replace(',', '.')) if stop_loss else None
        gain1 = float(gain1.replace(',', '.')) if gain1 else None
        gain2 = float(gain2.replace(',', '.')) if gain2 else None

        # Entry Date (default to today if missing)
        # Assuming form doesn't have it yet, set default. User can edit later or we add field.
        entry_date = date.today()

        new_asset = Asset(
            ticker=ticker, type=type_, strategy=strategy, quantity=qty, avg_price=price,
            stop_loss=stop_loss, gain1=gain1, gain2=gain2, recommendation=recommendation,
            entry_date=entry_date, fii_type=fii_type, sector=sector
        )
        db.session.add(new_asset)
        db.session.commit()
        
        # Fetch quote immediately for the new asset (Optimize: Single Fetch)
        try:
            quotes = get_quotes([ticker])
            if ticker in quotes:
                q = quotes[ticker]
                new_asset.current_price = q.get('price', 0.0)
                new_asset.daily_change = q.get('change_percent', 0.0)
                new_asset.last_update = datetime.now(ZoneInfo('America/Sao_Paulo'))
                db.session.commit()
        except Exception as e:
            print(f"Error fetching initial quote for {ticker}: {e}")
        
        if strategy == 'SWING':
            return redirect(url_for('swingtrade'))
        elif type_ == 'FII':
            return redirect(url_for('fiis'))
        else:
            return redirect(url_for('acoes'))
    return render_template('add.html')

@app.route('/delete/<int:id>')
@login_required
def delete_asset(id):
    asset = Asset.query.get_or_404(id)
    db.session.delete(asset)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_asset(id):
    asset = Asset.query.get_or_404(id)
    if request.method == 'POST':
        asset.ticker = request.form.get('ticker').upper()
        asset.type = request.form.get('type')
        asset.strategy = request.form.get('strategy', 'HOLDER')
        asset.quantity = int(request.form.get('quantity'))
        asset.avg_price = float(request.form.get('price').replace(',', '.'))
        
        stop_loss = request.form.get('stop_loss')
        gain1 = request.form.get('gain1')
        gain2 = request.form.get('gain2')
        recommendation = request.form.get('recommendation')
        fii_type = request.form.get('fii_type')
        sector = request.form.get('sector')
        
        asset.stop_loss = float(stop_loss.replace(',', '.')) if stop_loss else None
        asset.gain1 = float(gain1.replace(',', '.')) if gain1 else None
        asset.gain2 = float(gain2.replace(',', '.')) if gain2 else None
        asset.recommendation = recommendation
        asset.fii_type = fii_type
        asset.sector = sector
        
        db.session.commit()
        if asset.strategy == 'SWING':
            return redirect(url_for('swingtrade'))
        elif asset.type == 'FII':
            return redirect(url_for('fiis'))
        else:
            return redirect(url_for('acoes'))
    return render_template('add.html', asset=asset, edit=True)

@app.route('/buy/<int:id>', methods=['GET', 'POST'])
@login_required
def buy_asset(id):
    asset = Asset.query.get_or_404(id)
    if request.method == 'POST':
        qty_buy = int(request.form.get('quantity'))
        price_buy = float(request.form.get('price').replace(',', '.'))
        
        # Calculate New Average Price
        current_total = asset.quantity * asset.avg_price
        new_investment = qty_buy * price_buy
        total_qty = asset.quantity + qty_buy
        
        if total_qty > 0:
            new_avg_price = (current_total + new_investment) / total_qty
            asset.avg_price = new_avg_price
            asset.quantity = total_qty
            
            db.session.commit()
            flash(f'Compra registrada! Novo PM: R$ {new_avg_price:.2f}')
        
        if asset.type == 'FII':
            return redirect(url_for('fiis'))
        else:
            return redirect(url_for('acoes'))
            
    return render_template('buy.html', asset=asset, today=date.today().isoformat())

@app.route('/exit/<int:id>', methods=['GET', 'POST'])
@login_required
def exit_trade(id):
    asset = Asset.query.get_or_404(id)
    if request.method == 'POST':
        qty_sell = int(request.form.get('quantity'))
        price_sell = float(request.form.get('price').replace(',', '.'))
        date_sell = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        reason = request.form.get('reason')
        
        # Validation
        if qty_sell > asset.quantity:
            flash("Quantidade de saída maior que a disponível.")
            return redirect(url_for('exit_trade', id=id))

        # Calculate metrics
        avg_price = asset.avg_price
        total_sell = qty_sell * price_sell
        total_buy = qty_sell * avg_price
        profit_value = total_sell - total_buy
        profit_pct = (profit_value / total_buy * 100) if total_buy > 0 else 0
        
        # Days held
        days_held = (date_sell - asset.entry_date).days if asset.entry_date else 0
        
        # Record History
        history = TradeHistory(
            ticker=asset.ticker,
            strategy=asset.recommendation, # As requested: save Recommendation as Strategy
            entry_date=asset.entry_date,
            exit_date=date_sell,
            buy_price=avg_price,
            sell_price=price_sell,
            quantity=qty_sell,
            profit_value=profit_value,
            profit_pct=profit_pct,
            days_held=days_held,
            reason=reason
        )
        db.session.add(history)
        
        # Update Asset
        if qty_sell == asset.quantity:
            # Total Exit
            db.session.delete(asset)
            flash("Saída TOTAL registrada com sucesso!")
        else:
            # Partial Exit
            asset.quantity -= qty_sell
            flash("Saída PARCIAL registrada com sucesso!")
            
        db.session.commit()
        
        # Redirect back to origin
        if asset.strategy == 'SWING':
            return redirect(url_for('swingtrade'))
        elif asset.type == 'FII':
            return redirect(url_for('fiis'))
        else:
            return redirect(url_for('acoes'))
        
    return render_template('exit.html', asset=asset, today=date.today().isoformat())

@app.route('/historico')
@login_required
def history():
    trades = TradeHistory.query.order_by(TradeHistory.exit_date.desc()).all()
    return render_template('historico.html', history=trades)

@app.route('/resumo')
@login_required
def resumo():
    assets = Asset.query.all()
    history = TradeHistory.query.all()
    
    # 1. Total Equity & Allocation
    total_equity = 0
    total_acoes = 0
    total_fiis = 0
    total_swing = 0 # Maybe separate swing? User said Acoes vs FIIs.
    # Usually Swing is just a strategy, but Asset Type is ACAO/FII.
    # Let's split by TYPE for the "Allocation" chart.
    
    
    total_swing = 0 
    
    fii_types = {}
    stock_sectors = {} # New: [Sector] -> Value
    
    # FII Classification Mapping
    fii_map = {
        'LAJES CORPORATIVAS': 'Tijolo',
        'LOGISTICA': 'Tijolo',
        'SHOPPING CENTER': 'Tijolo',
        'HIBRIDO': 'Tijolo',
        'RENDA': 'Tijolo',
        'RECEBIVEIS': 'Papel',
        'FIAGRO': 'Papel',
        'FUNDO DE FUNDOS': 'Papel',
        'INFRA': 'Papel',
        'OUTROS': 'Papel' # Defaulting to Papel or maybe separate? Let's say Papel/Outros
    }
    
    # Data for table
    fii_summary = {} # {type: value}
    
    for a in assets:
        price = a.current_price if a.current_price > 0 else a.avg_price
        val = a.quantity * price
        
        total_equity += val
        
        if a.type == 'ACAO':
            total_acoes += val
            # Stock Sector:
            s = a.sector or 'Não Classificado'
            stock_sectors[s] = stock_sectors.get(s, 0) + val
            
        elif a.type == 'FII':
            total_fiis += val
            t = a.fii_type or 'OUTROS'
            # FII Breakdown for Chart
            fii_types[t] = fii_types.get(t, 0) + val
            # Summary for Table
            fii_summary[t] = fii_summary.get(t, 0) + val
            
    # Process FII Details for Table and Broad Chart
    fii_table_data = []
    broad_allocation = {'Tijolo': 0, 'Papel': 0}
    
    for t, val in fii_summary.items():
        category = fii_map.get(t, 'Papel') # Default to Papel if unknown
        broad_allocation[category] += val
        pct = (val / total_fiis * 100) if total_fiis > 0 else 0
        fii_table_data.append({
            'category': category,
            'type': t,
            'value': val,
            'pct': pct
        })
        
    # Sort table by Value desc
    fii_table_data.sort(key=lambda x: x['value'], reverse=True)
            
    # 2. Monthly Profit from History
    monthly_profit = {}
            
    # 2. Monthly Profit from History
    monthly_profit = {}
    for h in history:
        if h.exit_date:
            month_key = h.exit_date.strftime('%Y-%m')
            monthly_profit[month_key] = monthly_profit.get(month_key, 0) + h.profit_value
            
    # Sort months
    sorted_months = sorted(monthly_profit.keys())
    profit_data = [monthly_profit[k] for k in sorted_months]
    
    # NEW: Total Realized Profit Calculation
    total_realized_profit = sum(h.profit_value for h in history)
    
    return render_template('resumo.html', 
                         total_equity=total_equity, total_acoes=total_acoes, total_fiis=total_fiis,
                         total_realized_profit=sum(profit_data),
                         fii_types=fii_types,
                         fii_table=fii_table_data,
                         broad_allocation=broad_allocation,
                         months=sorted_months, profits=profit_data,
                         stock_sectors=stock_sectors)

@app.route('/edit_history/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_history(id):
    trade = TradeHistory.query.get_or_404(id)
    if request.method == 'POST':
        trade.ticker = request.form.get('ticker').upper()
        trade.strategy = request.form.get('strategy')
        trade.quantity = int(request.form.get('quantity'))
        trade.buy_price = float(request.form.get('buy_price').replace(',', '.'))
        trade.sell_price = float(request.form.get('sell_price').replace(',', '.'))
        
        entry_date = request.form.get('entry_date')
        exit_date = request.form.get('exit_date')
        trade.entry_date = datetime.strptime(entry_date, '%Y-%m-%d').date() if entry_date else None
        trade.exit_date = datetime.strptime(exit_date, '%Y-%m-%d').date() if exit_date else None
        trade.reason = request.form.get('reason')
        
        # Recalc
        total_buy = trade.quantity * trade.buy_price
        total_sell = trade.quantity * trade.sell_price
        trade.profit_value = total_sell - total_buy
        trade.profit_pct = (trade.profit_value / total_buy * 100) if total_buy > 0 else 0
        trade.days_held = (trade.exit_date - trade.entry_date).days if (trade.entry_date and trade.exit_date) else 0
        
        db.session.commit()
        return redirect(url_for('history'))
        
    return render_template('edit_history.html', trade=trade)

@app.route('/delete_history/<int:id>')
@login_required
def delete_history(id):
    trade = TradeHistory.query.get_or_404(id)
    db.session.delete(trade)
    db.session.commit()
    return redirect(url_for('history'))

@app.route('/add_history', methods=['GET', 'POST'])
@login_required
def add_history():
    if request.method == 'POST':
        ticker = request.form.get('ticker').upper()
        strategy = request.form.get('strategy')
        qty = int(request.form.get('quantity'))
        
        buy_price = float(request.form.get('buy_price').replace(',', '.'))
        sell_price = float(request.form.get('sell_price').replace(',', '.'))
        
        entry_date_str = request.form.get('entry_date')
        exit_date_str = request.form.get('exit_date')
        
        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date() if entry_date_str else None
        exit_date = datetime.strptime(exit_date_str, '%Y-%m-%d').date() if exit_date_str else None
        
        reason = request.form.get('reason')
        
        # Calculations
        total_buy = qty * buy_price
        total_sell = qty * sell_price
        profit_value = total_sell - total_buy
        profit_pct = (profit_value / total_buy * 100) if total_buy > 0 else 0
        days_held = (exit_date - entry_date).days if (entry_date and exit_date) else 0
        
        new_trade = TradeHistory(
            ticker=ticker,
            strategy=strategy,
            entry_date=entry_date,
            exit_date=exit_date,
            quantity=qty,
            buy_price=buy_price,
            sell_price=sell_price,
            profit_value=profit_value,
            profit_pct=profit_pct,
            days_held=days_held,
            reason=reason
        )
        db.session.add(new_trade)
        db.session.commit()
        
        return redirect(url_for('history'))
        
    return render_template('add_history.html')




@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        if api_key is not None:
            # Value is encrypted automatically by set_value
            Settings.set_value('brapi_token', api_key.strip())
            flash("Chave API atualizada com sucesso!")
        return redirect(url_for('config'))
    
    # Decrypted automatically by get_value
    current_key = Settings.get_value('brapi_token', '')
    if not current_key:
         current_key = os.environ.get('BRAPI_API_KEY', '')
         
    return render_template('config.html', current_key=current_key)

@app.route('/test_api', methods=['POST'])
@login_required
def test_api():
    ticker = request.form.get('ticker')
    if not ticker:
        flash("Informe um ticker.")
        return redirect(url_for('config'))
    
    import json
    success, data = get_raw_quote_data(ticker.strip().upper())
    formatted_data = json.dumps(data, indent=4, ensure_ascii=False)
    
    current_key = Settings.get_value('brapi_token', '') or os.environ.get('BRAPI_API_KEY', '')
    
    return render_template('config.html', 
                           current_key=current_key, 
                           test_result=formatted_data, 
                           success=success)

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            # Automatic Update on Login
            try:
                update_all_assets_logic()
            except:
                pass 
            return redirect(url_for('index'))
        flash('Usuário ou senha inválidos')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe')
            return redirect(url_for('register'))
            
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('register.html')




# ==========================================
# BALANCEAMENTO MODULE
# ==========================================

def get_maturity_class(maturity_date):
    if not maturity_date:
        return 'Indefinido'
    today = date.today()
    days = (maturity_date - today).days
    years = days / 365.0
    
    if years <= 2:
        return 'Curto Prazo'
    elif years <= 4:
        return 'Médio Prazo'
    else:
        return 'Longo Prazo'

@app.route('/fix_db')
def fix_db():
    try:
        # Run migration logic directly here
        conn = sqlite3.connect(os.path.join(app.instance_path, 'investments.db'))
        cursor = conn.cursor()
        columns = [
            ('category', 'TEXT DEFAULT "RV"'),
            ('description', 'TEXT'),
            ('invested_value', 'REAL')
        ]
        log = []
        for col_name, col_type in columns:
            try:
                cursor.execute(f"ALTER TABLE international ADD COLUMN {col_name} {col_type}")
                log.append(f"Added {col_name}")
            except Exception as e:
                log.append(f"Skipped {col_name}: {str(e)}")
        conn.commit()
        conn.close()
        return f"Migration Result: {', '.join(log)}. <a href='/balanceamento'>Voltar</a>"
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/fix_crypto_db')
def fix_crypto_db():
    try:
        conn = sqlite3.connect(os.path.join(app.instance_path, 'investments.db'))
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE crypto ADD COLUMN quote REAL")
            msg = "Added column 'quote' to crypto table."
        except Exception as e:
            msg = f"Error adding column: {str(e)}"
        
        conn.commit()
        conn.close()
        return f"{msg} <a href='/balanceamento'>Voltar</a>"
    except Exception as e:
        return f"Database Error: {str(e)}"

@app.route('/balanceamento')
@login_required
def balanceamento():
    # 1. Fetch Data
    rf_pos = FixedIncome.query.filter_by(category='POS').all()
    rf_pre = FixedIncome.query.filter_by(category='PRE').all()
    rf_ipca = FixedIncome.query.filter_by(category='IPCA').all()
    funds = InvestmentFund.query.all()
    cryptos = Crypto.query.all()
    pensions = Pension.query.all()
    
    try:
        intls_rv = International.query.filter((International.category == 'RV') | (International.category == None)).all()
        intls_rf = International.query.filter(International.category == 'RF').all()
    except Exception:
        # If column missing, redirect to fix
        return redirect(url_for('fix_db'))
    
    # 2. Existing Assets (Stocks/FIIs)
    assets = Asset.query.all()
    # Separate GOLD11 (Ouro) from other Stocks
    gold_assets = [a for a in assets if a.ticker == 'GOLD11']
    stock_assets = [a for a in assets if a.type == 'ACAO' and a.ticker != 'GOLD11']
    fii_assets = [a for a in assets if a.type == 'FII']

    val_ouro = sum([a.quantity * (a.current_price if a.current_price > 0 else a.avg_price) for a in gold_assets])
    val_acoes = sum([a.quantity * (a.current_price if a.current_price > 0 else a.avg_price) for a in stock_assets])
    val_fiis = sum([a.quantity * (a.current_price if a.current_price > 0 else a.avg_price) for a in fii_assets])
    
    # 3. Aggregates & Classification
    summary = {
        'Curto Prazo': 0, 'Médio Prazo': 0, 'Longo Prazo': 0, 'Indefinido': 0,
        'Renda Fixa': 0, 'Renda Variável': 0
    }
    
    types_total = {
        'Renda Fixa Pós': 0, 'Renda Fixa Pré': 0, 'Renda Fixa IPCA': 0,
        'Fundos': 0, 'Cripto': 0, 'Previdência': 0, 
        'Internacional RV': 0, 'Internacional RF': 0,
        'Ações': val_acoes, 'FIIs': val_fiis, 'Ouro': val_ouro
    }
    
    # Detailed Maturity Breakdown
    maturity_breakdown = {
        'Renda Fixa Pós': {'Curto Prazo': 0, 'Médio Prazo': 0, 'Longo Prazo': 0, 'Indefinido': 0},
        'Renda Fixa Pré': {'Curto Prazo': 0, 'Médio Prazo': 0, 'Longo Prazo': 0, 'Indefinido': 0},
        'Renda Fixa IPCA': {'Curto Prazo': 0, 'Médio Prazo': 0, 'Longo Prazo': 0, 'Indefinido': 0},
        'Fundos': {'Curto Prazo': 0, 'Médio Prazo': 0, 'Longo Prazo': 0, 'Indefinido': 0}
    }
    
    # Helper to process list
    def process_list(items, type_key, is_variable=False):
        total = 0
        for i in items:
            val = i.value if hasattr(i, 'value') else (i.current_value if hasattr(i, 'current_value') else i.value_usd * (i.rate_usd or 1))
            total += val
            
            # Maturity
            mat = i.maturity_date if hasattr(i, 'maturity_date') else None
            cls = get_maturity_class(mat)
            
            # Add to Global Summary
            if hasattr(i, 'maturity_date'):
               summary[cls] += val
            else:
               summary['Indefinido'] += val
               
            # Add to Detailed Breakdown if applicable
            if type_key in maturity_breakdown:
                maturity_breakdown[type_key][cls] += val

        types_total[type_key] = total
        if is_variable:
            summary['Renda Variável'] += total
        else:
            summary['Renda Fixa'] += total
        return total

    # Process Logic
    process_list(rf_pos, 'Renda Fixa Pós')
    process_list(rf_pre, 'Renda Fixa Pré')
    process_list(rf_ipca, 'Renda Fixa IPCA')
    process_list(funds, 'Fundos') # Funds can be RF or Variable, usually RF in this context/user image (pos fixado)
    
    # Crypto
    # Crypto Model has current_value
    t_crypto = sum([c.current_value for c in cryptos])
    types_total['Cripto'] = t_crypto
    summary['Renda Variável'] += t_crypto
    summary['Indefinido'] += t_crypto # Crypto has no maturity

    # Pension
    # Pension has type 'Acao' or 'Renda Fixa'
    for p in pensions:
        types_total['Previdência'] += p.value
        # Pension generally Long Term
        summary['Longo Prazo'] += p.value
        if p.type == 'Acao':
            summary['Renda Variável'] += p.value
        else:
            summary['Renda Fixa'] += p.value

    # International
    # International
    # RV
    t_intl_rv = sum([i.value_usd * (i.rate_usd or 5.5) for i in intls_rv])
    types_total['Internacional RV'] = t_intl_rv
    summary['Renda Variável'] += t_intl_rv
    summary['Indefinido'] += t_intl_rv

    # RF
    t_intl_rf = sum([i.value_usd * (i.rate_usd or 5.5) for i in intls_rf])
    types_total['Internacional RF'] = t_intl_rf
    summary['Renda Fixa'] += t_intl_rf
    summary['Longo Prazo'] += t_intl_rf # Assuming Bonds are long term

    # Add Stocks/FIIs/Gold to Summary
    summary['Renda Variável'] += (val_acoes + val_fiis + val_ouro)
    summary['Indefinido'] += (val_acoes + val_fiis + val_ouro) # Or Long Term? User requested classification. Equity is usually undefined or long. I will leave strict maturity for Fixed Income.

    total_portfolio = sum(types_total.values())

    # Filter breakdown to remove 0 values (Simpler for Template Rowspan)
    clean_breakdown = {}
    for cat, terms in maturity_breakdown.items():
        clean_terms = {k: v for k, v in terms.items() if v > 0.01}
        if clean_terms:
            clean_breakdown[cat] = clean_terms

    # Prepare Data for New Pie Charts (RF by Term, RF by Type)
    # 1. RF by Term (Aggregate from clean_breakdown)
    rf_chart_term = {'Curto Prazo': 0, 'Médio Prazo': 0, 'Longo Prazo': 0, 'Indefinido': 0}
    for cat, terms in clean_breakdown.items():
        for term, val in terms.items():
            if term in rf_chart_term:
                rf_chart_term[term] += val

    # 2. RF by Type (Aggregate Category Totals from clean_breakdown)
    rf_chart_type = {cat: sum(terms.values()) for cat, terms in clean_breakdown.items()}

    # 3. Total for the Table Footer
    total_rf_detailed = sum(rf_chart_type.values())

    # 4. Totals for International RV Table
    intl_rv_invested = sum([(i.quantity or 0) * (i.avg_price or 0) for i in intls_rv])
    intl_rv_current = sum([(i.quantity or 0) * (i.quote or 0) for i in intls_rv])
    intl_rv_profit = intl_rv_current - intl_rv_invested

    return render_template('balanceamento.html', 
                           rf_pos=rf_pos, rf_pre=rf_pre, rf_ipca=rf_ipca,
                           funds=funds, cryptos=cryptos, pensions=pensions, 
                           intls_rv=intls_rv, intls_rf=intls_rf,
                           summary=summary, types_total=types_total, total_portfolio=total_portfolio,
                           maturity_breakdown=clean_breakdown,
                           rf_chart_term=rf_chart_term, rf_chart_type=rf_chart_type,
                           total_rf_detailed=total_rf_detailed,
                           intl_rv_invested=intl_rv_invested, 
                           intl_rv_current=intl_rv_current, 
                           intl_rv_profit=intl_rv_profit)

@app.route('/balanceamento/add/rf', methods=['POST'])
@login_required
def add_rf():
    category = request.form.get('category')
    new_rf = FixedIncome(
        category=category,
        product_type=request.form.get('product_type'),
        institution=request.form.get('institution'),
        name=request.form.get('name'),
        value=float(request.form.get('value').replace('.','').replace(',','.')),
        rate=request.form.get('rate'),
        maturity_date=datetime.strptime(request.form.get('maturity_date'), '%Y-%m-%d').date() if request.form.get('maturity_date') else None
    )
    db.session.add(new_rf)
    db.session.commit()
    flash('Renda Fixa adicionada!', 'success')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/fund', methods=['POST'])
@login_required
def add_fund():
    new_fund = InvestmentFund(
        institution=request.form.get('institution'),
        name=request.form.get('name'),
        value=float(request.form.get('value').replace('.','').replace(',','.')),
        indexer=request.form.get('indexer'),
        maturity_date=datetime.strptime(request.form.get('maturity_date'), '%Y-%m-%d').date() if request.form.get('maturity_date') else None
    )
    db.session.add(new_fund)
    db.session.commit()
    flash('Fundo adicionado!', 'success')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/crypto', methods=['POST'])
@login_required
def add_crypto():
    new_crypto = Crypto(
        institution=request.form.get('institution'),
        name=request.form.get('name'),
        quantity=float(request.form.get('quantity').replace(',','.')),
        invested_value=float(request.form.get('invested_value').replace('.','').replace(',','.')),
        current_value=float(request.form.get('current_value').replace('.','').replace(',','.'))
    )
    db.session.add(new_crypto)
    db.session.commit()
    flash('Cripto adicionada!', 'success')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/pension', methods=['POST'])
@login_required
def add_pension():
    new_pension = Pension(
        institution=request.form.get('institution'),
        name=request.form.get('name'),
        value=float(request.form.get('value').replace('.','').replace(',','.')),
        type=request.form.get('type'),
        certificate=request.form.get('certificate')
    )
    db.session.add(new_pension)
    db.session.commit()
    flash('Previdência adicionada!', 'success')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/intl/rv', methods=['POST'])
@login_required
def add_intl_rv():
    qty = float(request.form.get('quantity').replace(',','.'))
    quote = float(request.form.get('quote').replace('.','').replace(',','.'))
    new_intl = International(
        category='RV',
        institution=request.form.get('institution'), # Broker
        name=request.form.get('name'), # Ticker
        quantity=qty,
        avg_price=float(request.form.get('avg_price').replace('.','').replace(',','.')),
        quote=quote,
        value_usd=qty * quote, # Total calculated
        rate_usd=float(request.form.get('rate_usd').replace(',','.')) if request.form.get('rate_usd') else 5.5
    )
    db.session.add(new_intl)
    db.session.commit()
    flash('Ação Internacional adicionada!', 'success')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/intl/rf', methods=['POST'])
@login_required
def add_intl_rf():
    new_intl = International(
        category='RF',
        institution=request.form.get('institution'), # Banco
        description=request.form.get('description'), # Tipo
        invested_value=float(request.form.get('invested_value').replace('.','').replace(',','.')),
        value_usd=float(request.form.get('value_usd').replace('.','').replace(',','.')), # Current Value
        name='RF INT', # Placeholder for non-ticker
        rate_usd=float(request.form.get('rate_usd').replace(',','.')) if request.form.get('rate_usd') else 5.5
    )
    db.session.add(new_intl)
    db.session.commit()
    flash('Renda Fixa Internacional adicionada!', 'success')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/edit/<type>/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_balance_item(type, id):
    if type == 'rf':
        item = FixedIncome.query.get_or_404(id)
    elif type == 'fund':
        item = InvestmentFund.query.get_or_404(id)
    elif type == 'crypto':
        item = Crypto.query.get_or_404(id)
    elif type == 'pension':
        item = Pension.query.get_or_404(id)
    elif type == 'intl':
        item = International.query.get_or_404(id)
    else:
        flash('Tipo inválido', 'error')
        return redirect(url_for('balanceamento'))
    
    if request.method == 'POST':
        # Common fields update could be dynamic, but manual is safer per type
        if type == 'rf':
            item.institution = request.form.get('institution')
            item.name = request.form.get('name')
            item.value = float(request.form.get('value').replace('.','').replace(',','.'))
            item.rate = request.form.get('rate')
            mat = request.form.get('maturity_date')
            item.maturity_date = datetime.strptime(mat, '%Y-%m-%d').date() if mat else None
            # Specifics
            if request.form.get('product_type'):
                item.product_type = request.form.get('product_type')
                
        elif type == 'fund':
            item.institution = request.form.get('institution')
            item.name = request.form.get('name')
            item.value = float(request.form.get('value').replace('.','').replace(',','.'))
            item.indexer = request.form.get('indexer')
            mat = request.form.get('maturity_date')
            item.maturity_date = datetime.strptime(mat, '%Y-%m-%d').date() if mat else None
            
        elif type == 'crypto':
            item.institution = request.form.get('institution')
            item.name = request.form.get('name')
            item.quantity = float(request.form.get('quantity').replace(',','.'))
            if request.form.get('invested_value'):
                item.invested_value = float(request.form.get('invested_value').replace('.','').replace(',','.'))
            item.current_value = float(request.form.get('current_value').replace('.','').replace(',','.'))
            
        elif type == 'pension':
            item.institution = request.form.get('institution')
            item.name = request.form.get('name')
            item.value = float(request.form.get('value').replace('.','').replace(',','.'))
            item.type = request.form.get('type')
            item.certificate = request.form.get('certificate')
            
        elif type == 'intl':
            item.rate_usd = float(request.form.get('rate_usd').replace(',','.'))
            if item.category == 'RF':
                 item.institution = request.form.get('institution')
                 item.description = request.form.get('description')
                 item.invested_value = float(request.form.get('invested_value').replace('.','').replace(',','.'))
                 item.value_usd = float(request.form.get('value_usd').replace('.','').replace(',','.'))
            else: # RV
                 item.institution = request.form.get('institution')
                 item.name = request.form.get('name')
                 
                 qty_str = request.form.get('quantity', '').replace(',', '.')
                 if qty_str and qty_str.lower() != 'none':
                     item.quantity = float(qty_str)
                 else:
                     item.quantity = 0.0

                 avg_str = request.form.get('avg_price', '').replace('.', '').replace(',', '.')
                 item.avg_price = float(avg_str) if avg_str and avg_str.lower() != 'none' else 0.0
                 
                 quote_str = request.form.get('quote', '').replace('.', '').replace(',', '.')
                 item.quote = float(quote_str) if quote_str and quote_str.lower() != 'none' else 0.0
                 
                 item.value_usd = (item.quantity or 0) * (item.quote or 0)
        
        db.session.commit()
        flash('Item atualizado com sucesso!', 'success')
        return redirect(url_for('balanceamento'))

    return render_template('edit_balance.html', item=item, type=type)

@app.route('/balanceamento/delete/<type>/<int:id>')
@login_required
def delete_balance_item(type, id):
    if type == 'rf':
        item = FixedIncome.query.get_or_404(id)
    elif type == 'fund':
        item = InvestmentFund.query.get_or_404(id)
    elif type == 'crypto':
        item = Crypto.query.get_or_404(id)
    elif type == 'pension':
        item = Pension.query.get_or_404(id)
    elif type == 'intl':
        item = International.query.get_or_404(id)
    else:
        flash('Tipo inválido', 'error')
        return redirect(url_for('balanceamento'))
    
    db.session.delete(item)
    db.session.commit()
    flash('Item removido!', 'success')
    return redirect(url_for('balanceamento'))


@app.route('/update_intl_quotes')
@login_required
def update_intl_quotes():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        msg_log = []

        # 1. Get USD Rate (USDBRL=X)
        usd_rate = 0.0
        try:
            url_usd = "https://query1.finance.yahoo.com/v8/finance/chart/USDBRL=X?interval=1d&range=1d"
            r_usd = requests.get(url_usd, headers=headers, timeout=10)
            data_usd = r_usd.json()
            usd_rate = data_usd['chart']['result'][0]['meta']['regularMarketPrice']
            msg_log.append(f"Dólar: R$ {usd_rate:.2f}")
        except Exception as e:
            msg_log.append(f"Erro Dólar: {str(e)}")
            print(f"Error fetching USD: {e}")

        if usd_rate > 0:
            # Update all International assets
            intls = International.query.all()
            for item in intls:
                # Update Exchange Rate for ALL
                item.rate_usd = usd_rate
                
                # If RV (Stocks), update Quote and Value
                if item.category == 'RV' and item.name:
                    try:
                        ticker_name = item.name.strip().upper()
                        # Common Corrections
                        if ticker_name == 'BRKB':
                            ticker_name = 'BRK-B'
                        
                        # Fetch Stock Quote
                        url_stock = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_name}?interval=1d&range=1d"
                        r_stock = requests.get(url_stock, headers=headers, timeout=10)
                        data_stock = r_stock.json()
                        
                        price = 0.0
                        if 'chart' in data_stock and 'result' in data_stock['chart'] and data_stock['chart']['result']:
                             price = data_stock['chart']['result'][0]['meta']['regularMarketPrice']
                        
                        if price > 0:
                            item.quote = price
                            msg_log.append(f"{ticker_name}: ${price:.2f}")
                            
                            # Recalculate Value USD: Quantity * Price
                            if item.quantity:
                                item.value_usd = item.quantity * price
                            else:
                                item.value_usd = 0.0
                        else:
                            msg_log.append(f"{ticker_name}: Não encontrado (API)")
                            
                    except Exception as e:
                        msg_log.append(f"{item.name}: Erro API {str(e)}")
                        print(f"Error updating {item.name}: {e}")
            
            # Update Cryptos
            cryptos = Crypto.query.all()
            for c in cryptos:
                if c.name: # e.g. BTC, ETH
                    try:
                        ticker_clean = c.name.strip().upper()
                        # Default to USD pair if not specified
                        # Try finding a valid Yahoo Ticker. Usually 'BTC-USD'
                        yahoo_ticker = f"{ticker_clean}-USD"
                        
                        url_crypto = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}?interval=1d&range=1d"
                        r_crypto = requests.get(url_crypto, headers=headers, timeout=10)
                        data_crypto = r_crypto.json()
                        
                        price_usd = 0.0
                        if 'chart' in data_crypto and 'result' in data_crypto['chart'] and data_crypto['chart']['result']:
                             price_usd = data_crypto['chart']['result'][0]['meta']['regularMarketPrice']
                        
                        if price_usd > 0:
                            # Convert to BRL
                            price_brl = price_usd * usd_rate
                            c.quote = price_brl
                            if c.quantity:
                                c.current_value = c.quantity * price_brl
                            msg_log.append(f"{ticker_clean}: R$ {price_brl:.2f}")
                        else:
                            msg_log.append(f"{ticker_clean}: Não encontrado")
                            
                    except Exception as e:
                        print(f"Error crypto {c.name}: {e}")
                        msg_log.append(f"{c.name}: Erro {str(e)}")

            db.session.commit()
            flash(f'Atualização Concluída! Detalhes: {", ".join(msg_log)}', 'success')
        else:
            flash(f'Não foi possível obter a cotação do Dólar. Detalhes: {", ".join(msg_log)}', 'warning')
            
    except Exception as e:
        flash(f'Erro fatal ao atualizar: {str(e)}', 'danger')
        
    return redirect(url_for('balanceamento'))
        
    return redirect(url_for('balanceamento'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')

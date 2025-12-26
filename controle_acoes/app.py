
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from models import db, Asset, Settings, User, TradeHistory
from services import get_quotes, get_raw_quote_data
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo

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

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

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
        entry_date = date.today()

        new_asset = Asset(
            ticker=ticker, type=type_, strategy=strategy, quantity=qty, avg_price=price,
            stop_loss=stop_loss, gain1=gain1, gain2=gain2, recommendation=recommendation,
            entry_date=entry_date, fii_type=fii_type
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
        
        asset.stop_loss = float(stop_loss.replace(',', '.')) if stop_loss else None
        asset.gain1 = float(gain1.replace(',', '.')) if gain1 else None
        asset.gain2 = float(gain2.replace(',', '.')) if gain2 else None
        asset.recommendation = recommendation
        asset.fii_type = fii_type
        
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
                           total_equity=total_equity,
                           total_acoes=total_acoes,
                           total_fiis=total_fiis,
                           total_realized_profit=total_realized_profit, # Pass to template
                           fii_types=fii_types,
                           months=sorted_months,
                           profits=profit_data,
                           fii_table=fii_table_data,
                           broad_allocation=broad_allocation)

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



if __name__ == '__main__':
    app.run(debug=True, port=5005)

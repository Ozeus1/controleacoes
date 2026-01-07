
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from models import db, Asset, Settings, User, TradeHistory, Option, FixedIncome, InvestmentFund, Crypto, Pension, International, Dividend
from services import get_quotes, get_raw_quote_data
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo
# import yfinance as yf -> Moved to local scope
import requests

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
    options = Option.query.filter_by(user_id=current_user.id).all()
    
    # Process options to add calculated fields and fetch underlying quotes
    processed_options = []
    
    # Get list of unique underlyings to fetch quotes
    underlyings = list(set([o.underlying_asset for o in options]))
    quotes = get_quotes(underlyings, user_id=current_user.id) if underlyings else {}
    
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
        try:
            ticker = request.form.get('ticker')
            underlying = request.form.get('underlying_asset') # Correct HTML name
            quantity_str = request.form.get('quantity')
            strike_str = request.form.get('strike_price') # Correct HTML name
            expiration_str = request.form.get('expiration_date') # Correct HTML name
            sale_price_str = request.form.get('sale_price')
            
            # Basic Validation
            if not all([ticker, underlying, quantity_str, strike_str, expiration_str, sale_price_str]):
                flash("Todos os campos são obrigatórios.", "warning")
                return redirect(url_for('add_option'))
            
            ticker = ticker.upper()
            underlying = underlying.upper()
            quantity = int(quantity_str)
            strike = float(strike_str.replace(',', '.'))
            expiration = datetime.strptime(expiration_str, '%Y-%m-%d').date()
            sale_price = float(sale_price_str.replace(',', '.'))
            
            # Current price (optional on add)
            curr_price_str = request.form.get('current_option_price')
            current_option_price = float(curr_price_str.replace(',', '.')) if curr_price_str else 0.0
            
            opt = Option(
                user_id=current_user.id,
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
            
            flash("Opção adicionada com sucesso!", "success")
            return redirect(url_for('opcoes'))
            
        except ValueError as ve:
            flash(f"Erro de formato: {ve}", "danger")
        except Exception as e:
            flash(f"Erro ao salvar opção: {e}", "danger")
            print(f"Error add_option: {e}")
            import traceback
            traceback.print_exc()
        
        return redirect(url_for('add_option'))
        
    return render_template('add_option.html')

@app.route('/edit_option/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_option(id):
    opt = Option.query.get_or_404(id)
    if opt.user_id != current_user.id:
        flash("Você não tem permissão para editar esta opção.")
        return redirect(url_for('opcoes'))
    if request.method == 'POST':
        try:
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
            flash("Opção atualizada com sucesso!", "success")
            return redirect(url_for('opcoes'))
            
        except ValueError as ve:
             flash(f"Erro de formato: {ve}", "danger")
        except Exception as e:
             flash(f"Erro ao editar: {e}", "danger")
             return redirect(url_for('opcoes'))
             
        return redirect(url_for('opcoes'))
        
    return render_template('add_option.html', option=opt, edit=True)

@app.route('/delete_option/<int:id>')
@login_required
def delete_option(id):
    opt = Option.query.get_or_404(id)
    if opt.user_id != current_user.id:
        flash("Você não tem permissão para deletar esta opção.")
        return redirect(url_for('opcoes'))
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
    if opt.user_id != current_user.id:
        flash("Você não tem permissão para fechar esta opção.")
        return redirect(url_for('opcoes'))
    
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
            user_id=current_user.id,
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
    # Stocks
    raw_assets = Asset.query.filter(Asset.type=='ACAO', Asset.user_id==current_user.id, Asset.quantity > 0).all()
    processed_assets = process_assets(raw_assets)
    
    total_invested = sum(a['total_invested'] for a in processed_assets)
    total_current = sum(a['current_total'] for a in processed_assets)

    # ETFs
    raw_etfs = Asset.query.filter(Asset.type=='ETF', Asset.user_id==current_user.id, Asset.quantity > 0).all()
    processed_etfs = process_assets(raw_etfs)
    
    total_etfs_invested = sum(a['total_invested'] for a in processed_etfs)
    total_etfs_current = sum(a['current_total'] for a in processed_etfs)
    
    return render_template('acoes.html', 
                           assets=processed_assets, 
                           total_invested=total_invested, 
                           total_current=total_current,
                           etfs=processed_etfs,
                           total_etfs_invested=total_etfs_invested,
                           total_etfs_current=total_etfs_current)

@app.route('/fiis')
@login_required
def fiis():
    raw_assets = Asset.query.filter(Asset.type=='FII', Asset.user_id==current_user.id, Asset.quantity > 0).all()
    processed_assets = process_assets(raw_assets)
    
    total_invested = sum(a['total_invested'] for a in processed_assets)
    total_current = sum(a['current_total'] for a in processed_assets)
    
    return render_template('fiis.html', assets=processed_assets, total_invested=total_invested, total_current=total_current)

@app.route('/swingtrade')
@login_required
def swingtrade():
    raw_assets = Asset.query.filter(Asset.strategy=='SWING', Asset.user_id==current_user.id, Asset.quantity > 0).all()
    assets = process_assets(raw_assets)
    return render_template('swingtrade.html', assets=assets)

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


# Valid update_all_assets_logic and update_quotes defined later (lines ~1433)


@app.route('/add_asset', methods=['GET', 'POST'])
@login_required
def add_asset():
    if request.method == 'POST':
        ticker = request.form.get('ticker').upper()
        type_ = request.form.get('type')
        
        try:
            qty = int(request.form.get('quantity'))
            avg_price_str = request.form.get('avg_price', '').replace(',', '.')
            avg_price = float(avg_price_str) if avg_price_str else 0.0
        except ValueError:
            flash("Erro: Quantidade ou Preço inválido.")
            return redirect(url_for('add_asset'))

        date_str = request.form.get('entry_date')
        
        # Check if exists
        asset = Asset.query.filter_by(ticker=ticker, user_id=current_user.id).first()
        if asset:
            # Update average price / quantity logic
            total_val = (asset.quantity * asset.avg_price) + (qty * avg_price)
            new_qty = asset.quantity + qty
            asset.avg_price = total_val / new_qty
            asset.quantity = new_qty
            flash(f'Ativo {ticker} atualizado! Nova quantidade: {new_qty}')
        else:
            entry_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
            sector = request.form.get('sector')
            fii_type = request.form.get('fii_type')
            
            # Fetch Initial Quote Data
            current_price = 0.0
            daily_change = 0.0
            last_update = None
            
            try:
                success, data = get_raw_quote_data(ticker)
                if success and 'regularMarketPrice' in data:
                     current_price = data['regularMarketPrice']
                     daily_change = data.get('regularMarketChangePercent', 0.0)
                     last_update = datetime.now()
            except Exception as e:
                print(f"Error fetching initial quote for {ticker}: {e}")
            
            asset = Asset(
                user_id=current_user.id,
                ticker=ticker, 
                type=type_, 
                quantity=qty, 
                avg_price=avg_price,
                entry_date=entry_date,
                sector=sector,
                fii_type=fii_type,
                current_price=current_price,
                daily_change=daily_change,
                last_update=last_update
            )
            db.session.add(asset)
            flash(f'Ativo {ticker} adicionado!')
        
        db.session.commit()
        if type_ == 'FII':
            return redirect(url_for('fiis'))
        elif type_ == 'ETF':
            return redirect(url_for('acoes'))
        else:
            return redirect(url_for('acoes'))
        
    return render_template('add.html')

@app.route('/delete_asset/<int:id>')
@login_required
def delete_asset(id):
    asset = Asset.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(asset)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_asset(id):
    asset = Asset.query.get_or_404(id)
    if asset.user_id != current_user.id:
        flash("Você não tem permissão para editar este ativo.")
        return redirect(url_for('index'))
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
    if asset.user_id != current_user.id:
        flash("Você não tem permissão para comprar mais deste ativo.")
        return redirect(url_for('index'))
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
    if asset.user_id != current_user.id:
        flash("Você não tem permissão para sair deste ativo.")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        try:
            qty_sell = int(request.form.get('quantity'))
            price_sell = float(request.form.get('price').replace(',', '.'))
            
            date_str = request.form.get('date')
            try:
                date_sell = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                date_sell = datetime.strptime(date_str, '%d/%m/%Y').date()
                
            reason = request.form.get('reason')
            
            # Validation
            if qty_sell > asset.quantity:
                flash("Quantidade de saída maior que a disponível.", "warning")
                return redirect(url_for('exit_trade', id=id))

            # Calculate metrics
            avg_price = asset.avg_price
            total_sell = qty_sell * price_sell
            total_buy = qty_sell * avg_price
            profit_value = total_sell - total_buy
            profit_pct = (profit_value / total_buy * 100) if total_buy > 0 else 0
            
            # Days held
            entry = asset.entry_date
            days_held = (date_sell - entry).days if entry else 0
            
            # Record History
            history = TradeHistory(
                user_id=current_user.id,
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
                # Total Exit - KEEP ASSET (Soft Delete) for Dividends
                asset.quantity = 0
                flash("Saída TOTAL registrada com sucesso!", "success")
            else:
                # Partial Exit
                asset.quantity -= qty_sell
                flash("Saída PARCIAL registrada com sucesso!", "success")
                
            db.session.commit()
            
            # Redirect back to origin
            if asset.strategy == 'SWING':
                return redirect(url_for('swingtrade'))
            elif asset.type == 'FII':
                return redirect(url_for('fiis'))
            else:
                return redirect(url_for('acoes'))
                
        except ValueError as e:
            flash(f"Erro de formato (Valores ou Data incorreta): {str(e)}", "danger")
            return redirect(url_for('exit_trade', id=id))
        except Exception as e:
            flash(f"Erro ao registrar saída: {str(e)}", "danger")
            print(f"Error exit_trade: {e}")
            return redirect(url_for('exit_trade', id=id))
        
    return render_template('exit.html', asset=asset, today=date.today().isoformat())

@app.route('/historico')
@login_required
def historico():
    trades = TradeHistory.query.filter_by(user_id=current_user.id).order_by(TradeHistory.exit_date.desc()).all()
    return render_template('historico.html', history=trades)

@app.route('/resumo')
@login_required
def resumo():
    # Calculate Summaries
    assets = Asset.query.filter(Asset.user_id==current_user.id, Asset.quantity > 0).all()
    history = TradeHistory.query.filter_by(user_id=current_user.id).all()
    
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
        
        elif a.type == 'ETF':
            # Add to separate total? Or lump with Acoes? User wanted separate in Acoes page.
            # Let's track separate total_etfs for allocation chart.
            # Initialize a new variable for this if needed, or pass in context.
            pass # Creating a separate aggregator below loop might be cleaner if we had initialized it. 
                 # But let's add logic here.
    
    # Re-loop or initialize above? Let's initialize total_etfs above.
    total_etfs = sum((a.quantity * (a.current_price if a.current_price > 0 else a.avg_price)) for a in assets if a.type == 'ETF')

            
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
                         total_equity=total_equity, total_acoes=total_acoes, total_fiis=total_fiis, total_etfs=total_etfs,
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
    if trade.user_id != current_user.id:
        flash("Você não tem permissão para editar este histórico.")
        return redirect(url_for('history'))
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
    if trade.user_id != current_user.id:
        flash("Você não tem permissão para deletar este histórico.")
        return redirect(url_for('history'))
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
            user_id=current_user.id,
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

@app.route('/history')
@login_required
def history():
    trades = TradeHistory.query.filter_by(user_id=current_user.id).order_by(TradeHistory.exit_date.desc()).all()
    
    total_profit = sum(t.profit_value for t in trades if t.profit_value)
    
    return render_template('history.html', trades=trades, total_profit=total_profit)




@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    if request.method == 'POST':
        brapi_key = request.form.get('brapi_key')
        if brapi_key:
             Settings.set_value('brapi_token', brapi_key, user_id=current_user.id)
             flash('Chave BRAPI salva com sucesso!')
        return redirect(url_for('config'))
        
    current_key = Settings.get_value('brapi_token', user_id=current_user.id)
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
    
    current_key = Settings.get_value('brapi_token', user_id=current_user.id)
    if not current_key:
        current_key = os.environ.get('BRAPI_API_KEY', '')
    
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
        log = []
        
        # 1. Quote
        try:
            cursor.execute("ALTER TABLE crypto ADD COLUMN quote REAL")
            log.append("Added 'quote'")
        except Exception as e:
            log.append(f"Skip quote: {str(e)}")
            
        # 2. Avg Price
        try:
            cursor.execute("ALTER TABLE crypto ADD COLUMN avg_price REAL DEFAULT 0.0")
            log.append("Added 'avg_price'")
        except Exception as e:
            log.append(f"Skip avg_price: {str(e)}")
        
        conn.commit()
        conn.close()
        return f"Migration: {', '.join(log)} <a href='/balanceamento'>Voltar</a>"
    except Exception as e:
        return f"Database Error: {str(e)}"

@app.route('/balanceamento')
@login_required
def balanceamento():
    # User Assets
        rfs = FixedIncome.query.filter_by(user_id=current_user.id).all()
        rf_pos = [r for r in rfs if r.category == 'POS']
        rf_pre = [r for r in rfs if r.category == 'PRE']
        rf_ipca = [r for r in rfs if r.category == 'IPCA']
        funds = InvestmentFund.query.filter_by(user_id=current_user.id).all()
        pensions = Pension.query.filter_by(user_id=current_user.id).all()
        
        # 2. RV Data
        acoes_assets = Asset.query.filter(Asset.type=='ACAO', Asset.user_id==current_user.id, Asset.quantity > 0).all()
        fiis_assets = Asset.query.filter(Asset.type=='FII', Asset.user_id==current_user.id, Asset.quantity > 0).all()
        etfs_assets = Asset.query.filter(Asset.type=='ETF', Asset.user_id==current_user.id, Asset.quantity > 0).all()
        cryptos = Crypto.query.filter_by(user_id=current_user.id).all()
        # Using same logic as models: strategy='SWING'
        assets_swing = Asset.query.filter_by(strategy='SWING', user_id=current_user.id).all()
        
        # 4. Stock Holders (Asset table)
        assets_holder = Asset.query.filter_by(strategy='HOLDER', type='ACAO', user_id=current_user.id).all()
        
        # Split Intls
        intls_rv = International.query.filter_by(user_id=current_user.id, category='RV').all()
        intls_rf = International.query.filter_by(user_id=current_user.id, category='RF').all()
        
        # 3. Swing Trade (using Asset table)
        # Using same logic as models: strategy='SWING'
        # assets_swing = Asset.query.filter_by(strategy='SWING', user_id=current_user.id).all() # This line was moved up
        
        # 4. Stock Holders (Asset table)
        # assets_holder = Asset.query.filter_by(strategy='HOLDER', type='ACAO', user_id=current_user.id).all() # This line was moved up
        fiis_holder = Asset.query.filter_by(strategy='HOLDER', type='FII', user_id=current_user.id).all()
        
        # 2. Existing Assets (Stocks/FIIs)
        assets = Asset.query.filter_by(user_id=current_user.id).all()
        # Separate GOLD11 (Ouro) from other Stocks
        gold_assets = [a for a in assets if a.ticker == 'GOLD11']
        stock_assets = [a for a in assets if a.type == 'ACAO' and a.ticker != 'GOLD11']
        fii_assets = [a for a in assets if a.type == 'FII']

        val_ouro = 0 # Ouro is deprecated/replaced by ETF logic, setting to 0 to avoid errors if referenced elsewhere

        val_acoes = sum((a.quantity * ((a.current_price or 0) if (a.current_price or 0) > 0 else (a.avg_price or 0))) for a in acoes_assets)
        val_fiis = sum((a.quantity * ((a.current_price or 0) if (a.current_price or 0) > 0 else (a.avg_price or 0))) for a in fiis_assets)
        val_etfs = sum((a.quantity * ((a.current_price or 0) if (a.current_price or 0) > 0 else (a.avg_price or 0))) for a in etfs_assets)
        val_cryptos = sum((c.quantity * ((c.current_price or 0) if (c.current_value or c.current_price) else (c.avg_price or 0))) for c in cryptos)
        val_intls_rv = sum((i.total_brl if i.total_brl else 0) for i in intls_rv)
        
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
                # Safe access to value or calculation
                if hasattr(i, 'value'):
                     val = i.value or 0
                elif hasattr(i, 'current_value'):
                     val = i.current_value or 0
                else:
                     val = (i.value_usd or 0) * (i.rate_usd or 1)
                
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
        # process_list(funds, 'Fundos') - Replaced by custom logic below
        
        # Special Processing for Funds (Chart Classification)
        total_funds = 0
        for f in funds:
            # Safe value access
            if hasattr(f, 'value'):
                 val = f.value or 0
            else:
                 val = 0
            
            total_funds += val
            
            # Maturity
            mat = f.maturity_date
            cls = get_maturity_class(mat)
            
            # Global Summary (Time & Type)
            if mat:
                summary[cls] += val
            else:
                summary['Indefinido'] += val
            
            # Determine Chart Category based on Indexer
            chart_cat = 'Fundos' 
            idx = (f.indexer or '').upper()
            if 'IPCA' in idx:
                chart_cat = 'Renda Fixa IPCA'
            elif 'SELIC' in idx or 'CDI' in idx:
                chart_cat = 'Renda Fixa Pós'
                
            # Add to Detailed Breakdown (for Chart)
            if chart_cat in maturity_breakdown:
                maturity_breakdown[chart_cat][cls] += val
        
        types_total['Fundos'] = total_funds
        summary['Renda Fixa'] += total_funds

        
        # Crypto
        # Crypto Model has current_value
        t_crypto = sum([(c.current_value or 0) for c in cryptos])
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
        t_intl_rv = sum([((i.value_usd or 0) * (i.rate_usd or 5.5)) for i in intls_rv])
        types_total['Internacional RV'] = t_intl_rv
        summary['Renda Variável'] += t_intl_rv
        summary['Indefinido'] += t_intl_rv

        # RF
        t_intl_rf = sum([((i.value_usd or 0) * (i.rate_usd or 5.5)) for i in intls_rf])
        types_total['Internacional RF'] = t_intl_rf
        summary['Renda Fixa'] += t_intl_rf
        summary['Longo Prazo'] += t_intl_rf # Assuming Bonds are long term

        # Add Stocks/FIIs/Gold (Gold replaced by ETF) to Summary
        # Add Stocks/FIIs to Summary (RV Brasil)
        summary['Renda Variável'] += (val_acoes + val_fiis)
        # Add ETF to Summary
        summary['Renda Variável'] += val_etfs
        summary['Indefinido'] += (val_acoes + val_fiis + val_etfs)

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

        # Prepare specific Pie Chart Data (Granular)
        # Requested: Renda Fixa Pós, Pré, IPCA, Fundos, Cripto, Previdência, Ações, FIIs, ETF (replacing Gold), Internacional RV, Internacional RF
        target_keys = [
            'Renda Fixa Pós', 'Renda Fixa Pré', 'Renda Fixa IPCA', 
            'Fundos', 'Cripto', 'Previdência', 
            'Ações', 'FIIs', 
            'Internacional RV', 'Internacional RF'
        ]
        # Dynamically add ETF to pie chart data, treating it as its own slice if desired, or under Intl.
        # User asked ETF to be where Gold was. Gold was in target_keys. 
        # I will add 'ETF' to target_keys to ensure it shows up in "Por Classe" chart if types_total has it.
        # But wait, types_total doesn't have 'ETF' key yet?
        # I need to add 'ETF' to types_total!
        
        types_total['ETF'] = val_etfs
        target_keys.append('ETF')

        pie_chart_data = {k: types_total.get(k, 0) for k in target_keys if types_total.get(k, 0) > 0.01}

        # 4. Totals for International RV Table
        intl_rv_invested = sum([((i.quantity or 0) * (i.avg_price or 0)) for i in intls_rv])
        intl_rv_current = sum([((i.quantity or 0) * (i.quote or 0)) for i in intls_rv])
        intl_rv_profit = intl_rv_current - intl_rv_invested
        
        # 5. Totals for Crypto Table
        # invested_value should match quantity * avg_price now, or use direct accumulation
        crypto_invested = sum([(c.quantity or 0) * (c.avg_price or 0) for c in cryptos])
        crypto_current = sum([(c.current_value or 0) for c in cryptos])
        crypto_profit = crypto_current - crypto_invested

        # 6. Location Breakdown (Brazil vs International)
        # International = Crypto + Intl RV + Intl RF + Gold
        # Note: t_intl_rf is calculated above. val_etfs is used as International per user request.
        total_intl = t_intl_rv + t_intl_rf + t_crypto + val_etfs
        total_br = total_portfolio - total_intl
        
        location_chart = {
            'Brasil': total_br,
            'Internacional': total_intl
        }

        # --- NEW SUMMARY CALCULATIONS (User Request) ---
        
        # 1. Hierarchical Data
        # Renda Fixa
        #   Pos: RF Pos + Funds (Pos) + Pension (RF)
        #   Pre: RF Pre
        #   Ipca: RF IPCA + Funds (Ipca)
        
        val_rf_pos_strict = types_total.get('Renda Fixa Pós', 0)
        # Funds classification logic was partly inside the loop, need to replicate or reuse
        # Let's re-iterate funds to split properly if not done
        val_funds_pos = 0
        val_funds_ipca = 0
        for f in funds:
            idx = (f.indexer or '').upper()
            val = f.value or 0
            if 'IPCA' in idx:
                val_funds_ipca += val
            else:
                val_funds_pos += val
        
        val_pension_rf = 0
        val_pension_acao = 0
        for p in pensions:
            p_val = p.value or 0
            if p.type == 'Acao':
                val_pension_acao += p_val
            else:
                val_pension_rf += p_val

        total_pos = val_rf_pos_strict + val_funds_pos + val_pension_rf
        total_pre = types_total.get('Renda Fixa Pré', 0)
        total_ipca = types_total.get('Renda Fixa IPCA', 0) + val_funds_ipca
        
        total_rf_general = total_pos + total_pre + total_ipca
        
        # ETF Calculation (New)
        val_etfs = sum((a.quantity * ((a.current_price or 0) if (a.current_price or 0) > 0 else (a.avg_price or 0))) for a in etfs_assets)

        # RV Brasil
        #   Acoes: Stocks + Pension Acao
        #   FII
        total_acoes_consol = val_acoes + val_pension_acao
        total_fii = val_fiis
        
        total_rv_br = total_acoes_consol + total_fii
        
        # RV Internacional
        #   Cripto
        #   RV Intl
        #   RF Intl
        #   ETF (Moved here as requested, replacing Gold role if any)
        
        total_cripto = types_total.get('Cripto', 0)
        total_intl_rv = types_total.get('Internacional RV', 0)
        total_intl_rf = types_total.get('Internacional RF', 0)
        total_etf_intl = val_etfs
        
        total_rv_intl_general = total_cripto + total_intl_rv + total_intl_rf + total_etf_intl
        
        # Data Structure for Template
        # Hierarchy List: [ {Group, Lines: [{Label, Val, Pct}, ...], Total, TotalPct}, ... ]
        
        def calc_pct(v):
            return (v / total_portfolio * 100) if total_portfolio > 0 else 0

        summary_hierarchy = [
            {
                'group': 'Renda Fixa',
                'lines': [
                    {'label': 'Pós', 'value': total_pos, 'pct': calc_pct(total_pos)},
                    {'label': 'Pré', 'value': total_pre, 'pct': calc_pct(total_pre)},
                    {'label': 'Ipca', 'value': total_ipca, 'pct': calc_pct(total_ipca)},
                ],
                'total': total_rf_general,
                'total_pct': calc_pct(total_rf_general)
            },
            {
                'group': 'RV Brasil',
                'lines': [
                    {'label': 'Ações', 'value': total_acoes_consol, 'pct': calc_pct(total_acoes_consol)},
                    {'label': 'FII', 'value': total_fii, 'pct': calc_pct(total_fii)},
                ],
                'total': total_rv_br,
                'total_pct': calc_pct(total_rv_br)
            },
            {
                'group': 'RV Internacional',
                'lines': [
                    {'label': 'Criptomoedas', 'value': total_cripto, 'pct': calc_pct(total_cripto)},
                    {'label': 'ETF', 'value': total_etf_intl, 'pct': calc_pct(total_etf_intl)},
                    {'label': 'Renda Variável Internacional', 'value': total_intl_rv, 'pct': calc_pct(total_intl_rv)},
                    {'label': 'Renda Fixa Internacional', 'value': total_intl_rf, 'pct': calc_pct(total_intl_rf)},
                ],
                'total': total_rv_intl_general,
                'total_pct': calc_pct(total_rv_intl_general)
            }
        ]
        
        # 2. Exploded Balance (For Pie Chart)
        # Using the individual lines from hierarchy
        summary_exploded = {}
        for group in summary_hierarchy:
            for line in group['lines']:
                if line['value'] > 0:
                    # Clean label for chart
                    label = line['label']
                    if label == 'Renda Variável Internacional': label = 'RV Internacional'
                    if label == 'Renda Fixa Internacional': label = 'RF Internacional'
                    summary_exploded[label] = line['value']
                    
        # 3. General Balance (For Donut Chart)
        # Categories: Pós, Pré, Ipca, RV Brasil, RV Internacional
        summary_general = {
            'Pós': total_pos,
            'Pré': total_pre,
            'Ipca': total_ipca,
            'RV Brasil': total_rv_br,
            'RV Internacional': total_rv_intl_general
        }

        return render_template('balanceamento.html', 
                               rf_pos=rf_pos, rf_pre=rf_pre, rf_ipca=rf_ipca,
                               funds=funds, cryptos=cryptos, pensions=pensions, 
                               intls_rv=intls_rv, intls_rf=intls_rf,
                               summary=summary, types_total=types_total, total_portfolio=total_portfolio,
                               maturity_breakdown=clean_breakdown,
                               rf_chart_term=rf_chart_term, rf_chart_type=rf_chart_type,
                               pie_chart_data=pie_chart_data,
                               total_rf_detailed=total_rf_detailed,
                               intl_rv_invested=intl_rv_invested, 
                               intl_rv_current=intl_rv_current, 
                               intl_rv_profit=intl_rv_profit,
                               crypto_invested=crypto_invested,
                               crypto_current=crypto_current,
                               crypto_profit=crypto_profit,
                               location_chart=location_chart,
                               summary_hierarchy=summary_hierarchy,
                               summary_exploded=summary_exploded,
                               summary_general=summary_general)
    except Exception as e:
        import traceback
        return f"<h3>Debug Error de Balanceamento (Mostre isso ao suporte):</h3><pre>{traceback.format_exc()}</pre>"

@app.route('/balanceamento/add/rf', methods=['POST'])
@login_required
def add_rf():
    new_rf = FixedIncome(
        user_id=current_user.id,
        category=request.form.get('category'),
        product_type=request.form.get('product_type'),
        institution=request.form.get('institution'),
        name=request.form.get('name'),
        value=float(request.form.get('value').replace(',', '.')),
        rate=request.form.get('rate'),
        maturity_date=datetime.strptime(request.form.get('maturity_date'), '%Y-%m-%d').date() if request.form.get('maturity_date') else None
    )
    db.session.add(new_rf)
    db.session.commit()
    flash('Renda Fixa adicionada!')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/fund', methods=['POST'])
@login_required
def add_fund():
    new_fund = InvestmentFund(
        user_id=current_user.id,
        institution=request.form.get('institution'),
        name=request.form.get('name'),
        value=float(request.form.get('value').replace(',', '.')),
        indexer=request.form.get('indexer'),
        maturity_date=datetime.strptime(request.form.get('maturity_date'), '%Y-%m-%d').date() if request.form.get('maturity_date') else None
    )
    db.session.add(new_fund)
    db.session.commit()
    flash('Fundo adicionado!')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/crypto', methods=['POST'])
@login_required
def add_crypto():
    qty_str = request.form.get('quantity', '').replace(',', '.')
    qty = float(qty_str) if qty_str else 0.0
    
    avg_price_str = request.form.get('avg_price', '').replace(',', '.') # User input for Avg Price
    avg_price = float(avg_price_str) if avg_price_str else 0.0
    
    # Clean logic
    invested_value = qty * avg_price
    
    # User might input current value manually or we calc later
    inv_val_str = request.form.get('invested_value')
    # If using form that sends invested_value (legacy), decide which to use. 
    # Current form has avg_price field?
    
    curr_val_str = request.form.get('current_value', '').replace(',', '.')
    current_value = float(curr_val_str) if curr_val_str else 0.0

    new_crypto = Crypto(
        user_id=current_user.id,
        institution=request.form.get('institution'),
        name=request.form.get('name'),
        quantity=qty,
        invested_value=invested_value,
        current_value=current_value,
        avg_price=avg_price
    )
    db.session.add(new_crypto)
    db.session.commit()
    flash('Cripto adicionada!')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/pension', methods=['POST'])
@login_required
def add_pension():
    new_pension = Pension(
        user_id=current_user.id,
        institution=request.form.get('institution'),
        name=request.form.get('name'),
        value=float(request.form.get('value').replace(',', '.')),
        type=request.form.get('type')
    )
    db.session.add(new_pension)
    db.session.commit()
    flash('Previdência adicionada!')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/add/intl', methods=['POST'])
@login_required
def add_intl():
    val_str = request.form.get('value_usd', '').replace(',', '.')
    val_usd = float(val_str) if val_str else 0.0
    
    qty_str = request.form.get('quantity', '').replace(',', '.')
    qty = float(qty_str) if qty_str else 0.0
    
    category = request.form.get('category', 'RV')
    
    quantity_str = request.form.get('quantity', '').replace(',', '.')
    qty = float(quantity_str) if quantity_str else 0.0
    
    avg_price_str = request.form.get('avg_price', '').replace(',', '.')
    avg_price = float(avg_price_str) if avg_price_str else 0.0
    
    # Optional direct value (legacy or override)
    value_usd_str = request.form.get('value_usd', '').replace(',', '.')
    val_usd_input = float(value_usd_str) if value_usd_str else 0.0
    
    # Code/Ticker
    ticker_name = request.form.get('name', '').upper()
    
    # Calculate Invested Value
    invested = 0.0
    if qty > 0 and avg_price > 0:
        invested = qty * avg_price
    elif val_usd_input > 0:
        invested = val_usd_input # Fallback for legacy RF
        
    # Initial Value USD (Current) -> equals invest if no quote yet
    current_val_usd = invested
    
    new_intl = International(
        user_id=current_user.id,
        institution=request.form.get('institution'),
        name=ticker_name,
        quantity=qty,
        avg_price=avg_price,
        category=category,
        description=request.form.get('description'),
        value_usd=current_val_usd,
        invested_value=invested,
        quote=avg_price # Set initial quote to purchase price
    )
    
    db.session.add(new_intl)
    db.session.commit()
    flash('Investimento Internacional adicionado!')
    return redirect(url_for('balanceamento'))

@app.route('/balanceamento/edit/<type>/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_balance_item(type, id):
    item = None
    if type == 'rf':
        item = FixedIncome.query.filter_by(id=id, user_id=current_user.id).first()
    elif type == 'fund':
        item = InvestmentFund.query.filter_by(id=id, user_id=current_user.id).first()
    elif type == 'crypto':
        item = Crypto.query.filter_by(id=id, user_id=current_user.id).first()
    elif type == 'pension':
        item = Pension.query.filter_by(id=id, user_id=current_user.id).first()
    elif type == 'intl':
        item = International.query.filter_by(id=id, user_id=current_user.id).first()
    
    if not item:
        flash('Item não encontrado ou acesso negado.')
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
            
            qty_str = request.form.get('quantity', '').replace(',', '.')
            if qty_str and qty_str.lower() != 'none':
                item.quantity = float(qty_str)
            else:
                item.quantity = 0.0
                
            avg_str = request.form.get('avg_price', '').replace('.', '').replace(',', '.')
            item.avg_price = float(avg_str) if avg_str and avg_str.lower() != 'none' else 0.0
            
            # Recalculate Invested from Avg * Qty
            item.invested_value = item.quantity * item.avg_price

            cur_str = request.form.get('current_value', '').replace('.', '').replace(',', '.')
            item.current_value = float(cur_str) if cur_str and cur_str.lower() != 'none' else 0.0
            
        elif type == 'pension':
            item.institution = request.form.get('institution')
            item.name = request.form.get('name')
            item.value = float(request.form.get('value').replace('.','').replace(',','.'))
            item.type = request.form.get('type')
            item.certificate = request.form.get('certificate')
            
        elif type == 'intl':
            item.rate_usd = float(request.form.get('rate_usd').replace(',','.'))
            if item.category == 'RF' and (not item.name or item.name == 'Renda Fixa'):
                 # Legacy RF or Manual
                 item.institution = request.form.get('institution')
                 item.description = request.form.get('description')
                 item.invested_value = float(request.form.get('invested_value').replace('.','').replace(',','.'))
                 item.value_usd = float(request.form.get('value_usd').replace('.','').replace(',','.'))
            else: # RV or New RF (Ticker-based)
                 item.institution = request.form.get('institution')
                 item.name = request.form.get('name')
                 item.description = request.form.get('description') # Preserve description for RF

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
    item = None
    if type == 'rf':
        item = FixedIncome.query.filter_by(id=id, user_id=current_user.id).first()
    elif type == 'fund':
        item = InvestmentFund.query.filter_by(id=id, user_id=current_user.id).first()
    elif type == 'crypto':
        item = Crypto.query.filter_by(id=id, user_id=current_user.id).first()
    elif type == 'pension':
        item = Pension.query.filter_by(id=id, user_id=current_user.id).first()
    elif type == 'intl':
        item = International.query.filter_by(id=id, user_id=current_user.id).first()
        
    if item:
        db.session.delete(item)
        db.session.commit()
        flash('Item removido!')
    else:
        flash('Item não encontrado ou acesso negado.')
        
    return redirect(url_for('balanceamento'))


def update_all_assets_logic():
    """
    Helper function to update quotes for all Stocks/FIIs of current user.
    """
    assets = Asset.query.filter_by(user_id=current_user.id).all()
    # Filter ACAO/FII
    relevant = [a for a in assets if a.type in ['ACAO', 'FII', 'ETF']]
    if not relevant:
        return 0, []
    
    updated_count = 0
    errors = []
    total_tried = 0

    # Chunk logic to avoid URL too long or timeouts
    chunk_size = 10
    relevant_chunks = [relevant[i:i + chunk_size] for i in range(0, len(relevant), chunk_size)]

    for chunk in relevant_chunks:
        try:
            tickers = [a.ticker for a in chunk]
            total_tried += len(tickers)
            quotes = get_quotes(tickers, user_id=current_user.id)
            
            if quotes:
                for asset in chunk:
                    # Generic lookup
                    quote_data = quotes.get(asset.ticker)
                    
                    if quote_data:
                        price = quote_data.get('price')
                        if price and price > 0:
                            asset.current_price = price
                            asset.daily_change = quote_data.get('change_percent', 0.0)
                            asset.last_update = datetime.now(ZoneInfo('America/Sao_Paulo'))
                            updated_count += 1
            
            # Commit after each chunk
            db.session.commit()
            
            # Respect API Rate Limit (Prevent 429 Too Many Requests)
            time.sleep(3)
            
        except Exception as e:
            print(f"Error updating chunk {tickers}: {e}")
            errors.append(str(e))
            continue
    
    return updated_count, total_tried, errors

@app.route('/update_quotes', methods=['POST'])
@login_required
def update_quotes():
    try:
        count, tried, errs = update_all_assets_logic()
        
        
        # Source is now Yahoo Finance (no token check needed)
        source_status = "Fonte: Yahoo Finance"
        
        if errs:
             # Show first error to help debug
             flash(f'Falha: {len(errs)} erros. Primeiro erro: {errs[0]}', 'warning')
        else:
             flash(f'Cotações atualizadas: {count}/{tried} ativos. {source_status}', 'success')
             
    except Exception as e:
        flash(f'Erro ao atualizar cotações: {str(e)}', 'danger')
        print(f"Error in update_quotes: {e}")
        import traceback
        traceback.print_exc()
        
    return redirect(request.referrer or url_for('index'))


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
                
                # Update Quote for RV and RF (if Ticker provided)
                if item.name and item.name.upper() != 'RENDA FIXA':
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

# --- User Management & Security ---

@app.before_request
def check_user_status():
    if current_user.is_authenticated:
        if current_user.expiry_date and current_user.expiry_date < date.today():
            logout_user()
            flash('Seu acesso expirou. Entre em contato com o administrador.', 'danger')
            return redirect(url_for('login'))

@app.route('/users')
@login_required
def list_users():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('resumo'))
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('resumo'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        expiry_str = request.form.get('expiry_date')
        
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe.', 'danger')
        else:
            expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date() if expiry_str else None
            user = User(username=username, role=role, expiry_date=expiry_date)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('list_users'))
            
    return render_template('add_user.html')

@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('resumo'))
        
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        user.role = request.form.get('role')
        expiry_str = request.form.get('expiry_date')
        user.expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date() if expiry_str else None
        
        new_pass = request.form.get('password')
        if new_pass:
            user.set_password(new_pass)
            
        db.session.commit()
        flash('Usuário atualizado!', 'success')
        return redirect(url_for('list_users'))
        
    return render_template('add_user.html', user=user, edit=True)

@app.route('/users/delete/<int:id>')
@login_required
def delete_user(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('resumo'))
    
    if id == current_user.id:
        flash('Você não pode excluir a si mesmo.', 'warning')
        return redirect(url_for('list_users'))

    user = User.query.get_or_404(id)
    # Optional: Delete all their data? For now standard delete.
    db.session.delete(user)
    db.session.commit()
    flash('Usuário removido.', 'success')
    return redirect(url_for('list_users'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        curr_pass = request.form.get('current_password')
        new_pass = request.form.get('new_password')
        confirm_pass = request.form.get('confirm_password')
        
        if not current_user.check_password(curr_pass):
            flash('Senha atual incorreta.', 'danger')
        elif new_pass != confirm_pass:
            flash('Novas senhas não conferem.', 'danger')
        else:
            current_user.set_password(new_pass)
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
            
    return render_template('profile.html')


# --- Dividends Module ---

@app.route('/balanceamento')
@login_required
def balanceamento():
    try:
        # User Assets
        assets = Asset.query.filter_by(user_id=current_user.id).all()
    
    # Filter only Stocks and FIIs for display
    relevant_assets = [a for a in assets if a.type in ['ACAO', 'FII']]
    
    # Get all dividends for user's assets
    all_dividends = db.session.query(Dividend).join(Asset).filter(Asset.user_id == current_user.id).order_by(Dividend.payment_date.desc()).all()
    
    today = date.today()
    
    # Split Received vs Provisioned
    dividends_received = [d for d in all_dividends if d.payment_date and d.payment_date <= today]
    dividends_provisioned = [d for d in all_dividends if d.payment_date and d.payment_date > today]
    
    # Calculate Totals (All time or just received?)
    total_received = sum(d.amount for d in dividends_received)
    
    # Pie Chart Data (Stocks vs FIIs - All Time Received)
    total_stocks = sum(d.amount for d in dividends_received if d.asset.type == 'ACAO')
    total_fiis = sum(d.amount for d in dividends_received if d.asset.type == 'FII')
    
    div_chart_data = {
        'Ações': total_stocks,
        'FIIs': total_fiis
    }
    
    # Monthly Evolution Data (Aggregation)
    from collections import defaultdict
    from dateutil.relativedelta import relativedelta
    
    # Struct: key(year, month) -> {'total': X, 'acoes': Y, 'fiis': Z}
    monthly_agg = defaultdict(lambda: {'total': 0.0, 'acoes': 0.0, 'fiis': 0.0})
    
    # Use ALL dividends (History + Future) to show evolution
    for div in all_dividends:
        if div.payment_date:
            key = (div.payment_date.year, div.payment_date.month)
            monthly_agg[key]['total'] += div.amount
            if div.asset.type == 'ACAO':
                monthly_agg[key]['acoes'] += div.amount
            elif div.asset.type == 'FII':
                monthly_agg[key]['fiis'] += div.amount
            
    # Determine Range (Standard 12 months context or based on data)
    # Let's align with the requested "Image 1/2" style which often shows rolling 12 months.
    # Default: Start from 11 months ago to next 1 month? Or simple sorted keys?
    # User data (01/2025 entry) means all data is >= Jan 2025.
    # If we stick to "Show what we have", it's safer.
    
    sorted_keys = sorted(monthly_agg.keys()) 
    
    monthly_labels = []
    values_total = []
    values_stocks = []
    values_fiis = []
    
    if sorted_keys:
        curr_y, curr_m = sorted_keys[0] # Start from first data point
        end_y, end_m = sorted_keys[-1]   # End at last data point
        
        # If range is huge, maybe limit? No, let's show all for now or last 15 months.
        # But if defaults to 12 months view? 
        # Let's enforce full range of available data for now since it's likely short (2025).
        
        current_iter = date(curr_y, curr_m, 1)
        end_iter = date(end_y, end_m, 1)
        
        while current_iter <= end_iter:
            k = (current_iter.year, current_iter.month)
            data = monthly_agg.get(k, {'total': 0.0, 'acoes': 0.0, 'fiis': 0.0})
            
            monthly_labels.append(current_iter.strftime('%b/%Y'))
            values_total.append(data['total'])
            values_stocks.append(data['acoes'])
            values_fiis.append(data['fiis'])
            
            current_iter += relativedelta(months=1)

    monthly_chart_data = {
        'labels': monthly_labels,
        'total': values_total,
        'acoes': values_stocks,
        'fiis': values_fiis
    }
    
    return render_template('dividendos.html', 
                           assets=relevant_assets, 
                           dividends_received=dividends_received,
                           dividends_provisioned=dividends_provisioned,
                           total_received=total_received,
                           div_chart_data=div_chart_data,
                           monthly_chart_data=monthly_chart_data)

@app.route('/update_dividends', methods=['POST'])
@login_required
def update_dividends():
    import yfinance as yf # Local import to prevent global crash
    assets = Asset.query.filter_by(user_id=current_user.id).filter(Asset.type.in_(['ACAO', 'FII', 'ETF'])).all()
    
    updated_count = 0
    error_count = 0
    
    for asset in assets:
        try:
            ticker_sa = f"{asset.ticker}.SA" if not asset.ticker.endswith('.SA') else asset.ticker
            yf_ticker = yf.Ticker(ticker_sa)
            
            # Fetch Dividends History
            # If entry_date exists, fetch from that date. Else last 1 year.
            start_date = asset.entry_date
            if not start_date:
                 # Default to 1 year ago if no entry date
                 start_date = date.today().replace(year=date.today().year - 1)
            
            # YFinance expects string or datetime
            history = yf_ticker.dividends
            
            # Clear existing dividends for this asset to avoid duplicates/stale data
            Dividend.query.filter_by(asset_id=asset.id).delete()
            
            for dt, amount in history.items():
                # dt is Timestamp, convert to date
                div_date = dt.date()
                
                if div_date >= start_date:
                    div_type = 'Dividendo'
                    if asset.ticker.endswith('11') or asset.ticker.endswith('11B'):
                        div_type = 'Rendimento'
                        
                    new_div = Dividend(
                        asset_id=asset.id,
                        ticker=asset.ticker,
                        type=div_type, 
                        amount=float(amount) * asset.quantity, 
                        payment_date=div_date,
                        ex_date=div_date # YF date is usually Ex-Date
                    )
                    db.session.add(new_div)
            
            updated_count += 1
            
        except Exception as e:
            print(f"Error fetching dividends for {asset.ticker}: {e}")
            error_count += 1
            continue
            
    db.session.commit()
    msg = f'Dados atualizados! (Sucesso: {updated_count}, Erros: {error_count})'
    if error_count > 0:
        flash(msg, 'warning')
    else:
        flash(msg, 'success')
    return redirect(url_for('dividendos'))

@app.route('/update_asset_date/<int:id>', methods=['POST'])
@login_required
def update_asset_date(id):
    asset = Asset.query.get_or_404(id)
    if asset.user_id != current_user.id:
        return "Unauthorized", 403
        
    new_date_str = request.form.get('entry_date')
    if new_date_str:
        try:
            asset.entry_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
            db.session.commit()
            flash(f'Data de compra de {asset.ticker} atualizada.', 'success')
        except ValueError:
            flash('Formato de data inválido.', 'danger')
    
    return redirect(url_for('dividendos'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')

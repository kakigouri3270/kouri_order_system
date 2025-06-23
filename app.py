from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import time

app = Flask(__name__)

ORDERS_FILE = 'orders.json'
TIMEOUT = 600  # 10分
ORDERS_PER_PAGE = 10  # 1ページあたりの表示数

def load_orders():
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"orders": [], "current": 0}, f, ensure_ascii=False, indent=2)
    with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_orders(data):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

@app.route('/')
def home():
    return redirect(url_for('order'))

@app.route('/order', methods=['GET', 'POST'])
def order():
    data = load_orders()
    if request.method == 'POST':
        items = request.form.getlist('item')
        quantities = request.form.getlist('quantity')
        order_items = []
        for item, qty in zip(items, quantities):
            if int(qty) > 0:
                order_items.append({"name": item, "quantity": int(qty)})

        new_number = len(data['orders']) + 1
        timestamp = time.time()
        data['orders'].append({
            "number": new_number,
            "items": order_items,
            "timestamp": timestamp,
            "status": "waiting"
        })
        save_orders(data)
        return render_template('confirm.html', number=new_number)

    menu = ['焼きそば', 'ケバブ', 'ラムネ', 'カルピスウォーター', '麦茶']
    return render_template('order.html', menu=menu, current=data.get('current', 0))

@app.route('/admin')
def admin():
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)

    all_data = load_orders()
    all_orders = all_data['orders']

    if status_filter != 'all':
        filtered_orders = [o for o in all_orders if o['status'] == status_filter]
    else:
        filtered_orders = all_orders

    filtered_orders.sort(key=lambda o: o['number'], reverse=True)

    total_orders = len(filtered_orders)
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    page_orders = filtered_orders[start:end]

    current = next((o['number'] for o in all_orders if o['status'] == 'called'), 'なし')
    total_pages = (total_orders + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE

    return render_template(
        'admin.html',
        orders=page_orders,
        status_filter=status_filter,
        current=current,
        page=page,
        total_pages=total_pages
    )

@app.route('/mark_called/<int:number>', methods=['POST'])
def mark_called(number):
    data = load_orders()
    updated = False
    now = time.time()
    for order in data['orders']:
        if order['number'] == number:
            order['status'] = 'called'
            order['timestamp'] = now   # ← ここを追加
            data['current'] = number
            updated = True
            break
    save_orders(data)

    if is_ajax():
        return jsonify({"success": updated})
    else:
        return redirect(url_for('admin'))

@app.route('/mark_received/<int:number>', methods=['POST'])
def mark_received(number):
    data = load_orders()
    updated = False
    for order in data['orders']:
        if order['number'] == number:
            order['status'] = 'done'
            updated = True
            break
    save_orders(data)

    if is_ajax():
        return jsonify({"success": updated})
    else:
        return redirect(url_for('admin'))

@app.route('/mark_skipped/<int:number>', methods=['POST'])
def mark_skipped(number):
    data = load_orders()
    updated = False
    for order in data['orders']:
        if order['number'] == number:
            order['status'] = 'skipped'
            updated = True
            break
    save_orders(data)

    if is_ajax():
        return jsonify({"success": updated})
    else:
        return redirect(url_for('admin'))

@app.route('/mark_cancelled/<int:number>', methods=['POST'])
def mark_cancelled(number):
    data = load_orders()
    updated = False
    for order in data['orders']:
        if order['number'] == number:
            order['status'] = 'cancelled'
            updated = True
            break
    save_orders(data)

    if is_ajax():
        return jsonify({"success": updated})
    else:
        return redirect(url_for('admin'))

@app.route('/api/orders')
def api_orders():
    data = load_orders()
    return jsonify(data['orders'])

@app.route('/reset_all', methods=['POST'])
def reset_all():
    save_orders({"orders": [], "current": 0})
    return redirect(url_for('admin'))

@app.route('/api/order_status/<int:number>')
def api_order_status(number):
    data = load_orders()
    for order in data['orders']:
        if order['number'] == number:
            return jsonify({"status": order['status']})
    return jsonify({"status": "not_found"})

@app.route('/reset_confirm')
def reset_confirm():
    return render_template('reset_confirm.html')

@app.route('/kiosk', methods=['GET', 'POST'])
def kiosk_order():
    data = load_orders()
    menu = ['焼きそば', 'ケバブ', 'ラムネ', 'カルピスウォーター', '麦茶']

    if request.method == 'POST':
        items = request.form.getlist('item')
        quantities = request.form.getlist('quantity')
        order_items = []
        for item, qty in zip(items, quantities):
            if int(qty) > 0:
                order_items.append({"name": item, "quantity": int(qty)})

        new_number = len(data['orders']) + 1
        timestamp = time.time()
        data['orders'].append({
            "number": new_number,
            "items": order_items,
            "timestamp": timestamp,
            "status": "waiting"
        })
        save_orders(data)

        return render_template('kiosk_confirm.html', number=new_number)

    return render_template('kiosk_order.html', menu=menu, current=data.get('current', 0))

@app.route('/api/current_number')
def api_current_number():
    data = load_orders()
    called_numbers = [order['number'] for order in data['orders'] if order['status'] == 'called']
    return jsonify({"current_numbers": called_numbers})

@app.route('/current')
def current():
    data = load_orders()
    called_orders = [order for order in data['orders'] if order['status'] == 'called']
    current_number = called_orders[0]['number'] if called_orders else 0
    return render_template('current.html', current=current_number)

@app.route('/api/check_and_update_status')
def check_and_update_status():
    data = load_orders()
    now = time.time()
    updated = False

    for order in data['orders']:
        if order['status'] == 'called':
            elapsed = now - order['timestamp']
            if elapsed > 600:
                order['status'] = 'cancelled'
                updated = True
            elif elapsed > 300:
                order['timestamp'] = now  # 5分経過で再呼び出し
                updated = True

    if updated:
        save_orders(data)

    return jsonify({"updated": updated})

@app.route('/waiting/<int:number>')
def waiting(number):
    return render_template('waiting.html', number=number)

if __name__ == '__main__':
    app.run(debug=True)

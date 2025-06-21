from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import time

app = Flask(__name__)

ORDERS_FILE = 'orders.json'
TIMEOUT = 600  # 10分

def load_orders():
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"orders": [], "current": 0}, f, ensure_ascii=False, indent=2)
    with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_orders(data):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    data = load_orders()
    now = time.time()
    for order in data['orders']:
        if order['status'] == 'waiting' and now - order['timestamp'] > TIMEOUT:
            order['status'] = 'skipped'
    save_orders(data)

    status_filter = request.args.get('status', 'all')
    if status_filter == 'all':
        filtered_orders = data['orders']
    else:
        filtered_orders = [o for o in data['orders'] if o['status'] == status_filter]

    return render_template('admin.html', orders=filtered_orders, current=data['current'], status_filter=status_filter)

@app.route('/mark_called/<int:number>', methods=['POST'])
def mark_called(number):
    data = load_orders()
    for order in data['orders']:
        if order['number'] == number:
            order['status'] = 'called'
            data['current'] = number
            break
    save_orders(data)
    return redirect(url_for('admin'))

@app.route('/mark_received/<int:number>', methods=['POST'])
def mark_received(number):
    data = load_orders()
    for order in data['orders']:
        if order['number'] == number:
            order['status'] = 'done'
            break
    save_orders(data)
    return redirect(url_for('admin'))

@app.route('/mark_skipped/<int:number>', methods=['POST'])
def mark_skipped(number):
    data = load_orders()
    for order in data['orders']:
        if order['number'] == number:
            order['status'] = 'skipped'
            break
    save_orders(data)
    return redirect(url_for('admin'))

@app.route('/mark_cancelled/<int:number>', methods=['POST'])
def mark_cancelled(number):
    data = load_orders()
    for order in data['orders']:
        if order['number'] == number:
            order['status'] = 'cancelled'
            break
    save_orders(data)
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

        # 注文完了後は確認ページに遷移
        return render_template('kiosk_confirm.html', number=new_number)

    return render_template('kiosk_order.html', menu=menu, current=data.get('current', 0))

@app.route('/api/current_number')
def api_current_number():
    data = load_orders()
    # 呼び出し中の注文すべての番号をリストとして返す
    called_numbers = [order['number'] for order in data['orders'] if order['status'] == 'called']
    return jsonify({"current_numbers": called_numbers})

@app.route('/current')
def current():
    data = load_orders()
    # 呼び出し中の注文番号を初期表示用に渡す（無くても動く）
    called_orders = [order for order in data['orders'] if order['status'] == 'called']
    current_number = called_orders[0]['number'] if called_orders else 0
    return render_template('current.html', current=current_number)



if __name__ == '__main__':
    app.run(debug=True)



import os
import sqlite3
from flask import Flask, render_template, request, redirect, make_response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

# ================= BANCO =================

def conectar():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'enquete.db'))
    conn.row_factory = sqlite3.Row
    return conn

def criar_banco():
    conn = conectar()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS votos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opcao TEXT NOT NULL,
            cidade TEXT,
            bairro TEXT,
            ip TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ================= ROTAS =================

@app.route('/')
def index():
    ja_votou = request.cookies.get('votou')
    return render_template('index.html', ja_votou=ja_votou)


@app.route('/votar', methods=['POST'])
def votar():
    if request.cookies.get('votou'):
        return redirect('/resultado')

    opcao = request.form['opcao']
    cidade = request.form['cidade'].strip().upper()
    bairro = request.form['bairro'].strip().upper()

    ip = request.remote_addr

    conn = conectar()
    conn.execute(
        'INSERT INTO votos (opcao, cidade, bairro, ip) VALUES (?, ?, ?, ?)',
        (opcao, cidade, bairro, ip)
    )
    conn.commit()
    conn.close()

    resp = make_response(redirect('/resultado'))
    resp.set_cookie('votou', 'sim', max_age=60*60*24*30)
    return resp
@app.route('/resultado')
def resultado():
    conn = conectar()

    votos = conn.execute(
        'SELECT opcao, COUNT(*) as total FROM votos GROUP BY opcao'
    ).fetchall()

    bairros = conn.execute(
        'SELECT bairro, COUNT(*) as total FROM votos GROUP BY bairro ORDER BY total DESC LIMIT 5'
    ).fetchall()

    cidades = conn.execute(
        'SELECT cidade, COUNT(*) as total FROM votos GROUP BY cidade ORDER BY total DESC LIMIT 5'
    ).fetchall()

    conn.close()

    total_geral = sum([d['total'] for d in votos]) or 1

    resultados = []
    labels = []
    valores = []

    for d in votos:
        porcentagem = round((d['total'] / total_geral) * 100, 1)
        resultados.append({
            'opcao': d['opcao'],
            'total': d['total'],
            'porcentagem': porcentagem
        })
        labels.append(d['opcao'])
        valores.append(d['total'])

    bairros_labels = [b['bairro'] for b in bairros]
    bairros_valores = [b['total'] for b in bairros]

    cidades_labels = [c['cidade'] for c in cidades]
    cidades_valores = [c['total'] for c in cidades]

    return render_template(
        'resultado.html',
        resultados=resultados,
        total_geral=total_geral,
        labels=labels,
        valores=valores,
        bairros_labels=bairros_labels,
        bairros_valores=bairros_valores,
        cidades_labels=cidades_labels,
        cidades_valores=cidades_valores
    )



# ================= INICIAR =================

if __name__ == '__main__':
    criar_banco()
    app.run(debug=True, port=5002)


if __name__ == '__main__':
    criar_banco()
    app.run(host='0.0.0.0', port=5002)

from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "chave-fixa-enquete-2026"

RESETAR_BANCO = True  # 🔥 DEIXE TRUE SÓ AGORA

# ================= BANCO =================

def conectar():
    conn = sqlite3.connect('enquete.db')
    conn.row_factory = sqlite3.Row
    return conn

def resetar_banco():
    caminho = os.path.join(os.getcwd(), "enquete.db")
    if os.path.exists(caminho):
        os.remove(caminho)
        print("BANCO APAGADO COM SUCESSO")

def criar_banco():
    conn = conectar()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS votos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opcao TEXT,
            cidade TEXT,
            bairro TEXT,
            ip TEXT
        )
    ''')
    conn.commit()
    conn.close()

if RESETAR_BANCO:
    resetar_banco()

criar_banco()

# ================= ROTAS =================

@app.route('/')
def index():
    return render_template('voto.html')


@app.route('/votar', methods=['POST'])
def votar():
    if 'votou' in session:
        return redirect('/resultado')

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    conn = conectar()

    ja_votou = conn.execute(
        'SELECT id FROM votos WHERE ip = ?',
        (ip,)
    ).fetchone()

    if ja_votou:
        conn.close()
        return redirect('/resultado')

    opcao = request.form['opcao']
    cidade = request.form['cidade'].strip().upper()
    bairro = request.form['bairro'].strip().upper()

    conn.execute(
        'INSERT INTO votos (opcao, cidade, bairro, ip) VALUES (?, ?, ?, ?)',
        (opcao, cidade, bairro, ip)
    )

    conn.commit()
    conn.close()

    session['votou'] = True
    return redirect('/resultado')


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

    return render_template(
        'resultado.html',
        resultados=resultados,
        total_geral=total_geral,
        labels=labels,
        valores=valores,
        bairros_labels=[b['bairro'] for b in bairros],
        bairros_valores=[b['total'] for b in bairros],
        cidades_labels=[c['cidade'] for c in cidades],
        cidades_valores=[c['total'] for c in cidades]
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)

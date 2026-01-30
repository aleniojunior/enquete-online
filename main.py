from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "chave-secreta-fixa-aqui-123"  # impede reset de sessão a cada reinício

# ================== BANCO ==================

def conectar():
    conn = sqlite3.connect('enquete.db')
    conn.row_factory = sqlite3.Row
    return conn

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

# 🧨 RESET TEMPORÁRIO DO BANCO (USAR SÓ AGORA)
def resetar_banco():
    if os.path.exists("enquete.db"):
        os.remove("enquete.db")

# ================== ROTAS ==================

@app.route('/')
def index():
    return render_template('voto.html')


@app.route('/votar', methods=['POST'])
def votar():
    # Bloqueio por sessão
    if 'votou' in session:
        return redirect('/resultado')

    # Pega IP real mesmo atrás do Render
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    conn = conectar()

    # Bloqueio por IP
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

# ================== INICIAR APP ==================

if __name__ == '__main__':
    resetar_banco()   # 🧨 ZERA O BANCO AGORA (REMOVER DEPOIS)
    criar_banco()
    app.run(host='0.0.0.0', port=5002)

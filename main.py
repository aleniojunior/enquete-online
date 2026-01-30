from flask import Flask, render_template, request, redirect, session
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "chave-fixa-enquete-2026"

DATABASE_URL = os.getenv("DATABASE_URL")

# ================= BANCO POSTGRES =================

def conectar():
    return psycopg2.connect(DATABASE_URL)

def criar_tabela():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS votos (
            id SERIAL PRIMARY KEY,
            opcao TEXT,
            cidade TEXT,
            bairro TEXT,
            ip TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

criar_tabela()

# ================= ROTAS =================

@app.route('/')
def index():
    return render_template('voto.html')


@app.route('/votar', methods=['POST'])
def votar():
    # Bloqueio por sessão
    if 'votou' in session:
        return redirect('/resultado')

    # Pega IP real na Render
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    conn = conectar()
    cur = conn.cursor()

    # Bloqueio por IP
    cur.execute("SELECT id FROM votos WHERE ip = %s", (ip,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return redirect('/resultado')

    opcao = request.form['opcao']
    cidade = request.form['cidade'].strip().upper()
    bairro = request.form['bairro'].strip().upper()

    cur.execute(
        "INSERT INTO votos (opcao, cidade, bairro, ip) VALUES (%s, %s, %s, %s)",
        (opcao, cidade, bairro, ip)
    )

    conn.commit()
    cur.close()
    conn.close()

    session['votou'] = True
    return redirect('/resultado')


@app.route('/resultado')
def resultado():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT opcao, COUNT(*) FROM votos GROUP BY opcao")
    votos = cur.fetchall()

    cur.execute("SELECT bairro, COUNT(*) FROM votos GROUP BY bairro ORDER BY COUNT(*) DESC LIMIT 5")
    bairros = cur.fetchall()

    cur.execute("SELECT cidade, COUNT(*) FROM votos GROUP BY cidade ORDER BY COUNT(*) DESC LIMIT 5")
    cidades = cur.fetchall()

    cur.close()
    conn.close()

    total_geral = sum(v[1] for v in votos) or 1

    resultados = []
    labels = []
    valores = []

    for opcao, total in votos:
        porcentagem = round((total / total_geral) * 100, 1)
        resultados.append({
            'opcao': opcao,
            'total': total,
            'porcentagem': porcentagem
        })
        labels.append(opcao)
        valores.append(total)

    return render_template(
        'resultado.html',
        resultados=resultados,
        total_geral=total_geral,
        labels=labels,
        valores=valores,
        bairros_labels=[b[0] for b in bairros],
        bairros_valores=[b[1] for b in bairros],
        cidades_labels=[c[0] for c in cidades],
        cidades_valores=[c[1] for c in cidades]
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)

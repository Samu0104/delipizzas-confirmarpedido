from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '123'

def get_db_connection():
    try:
        conn = sqlite3.connect('BancoDeDados.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def create_table():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_pizza(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_pizza TEXT NOT NULL,
                descricao TEXT NOT NULL,
                preco REAL NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_sobremesa(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_sobremesa TEXT NOT NULL,
                preco REAL NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_bebidas(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_bebida TEXT NOT NULL,
                preco REAL NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conta(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                idade INTEGER NOT NULL,
                telefone TEXT NOT NULL,
                senha TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carrinho(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                nome TEXT NOT NULL,
                preco REAL NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total REAL NOT NULL,
                data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES conta (id)
            )
        ''')

        cursor.execute("SELECT COUNT(*) FROM cardapio_pizza")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
            INSERT INTO cardapio_pizza (nome_pizza, descricao, preco) VALUES (?, ?, ?)
            ''', [
                ("Pizza Marguerita", "molho de tomate, queijo, manjericão", 30.00),
                ("Pizza Calabresa", "molho de tomate, calabresa, queijo", 35.00),
                ("Pizza Quatro Queijos", "molho de tomate, queijo mussarela, queijo parmesão, queijo cheddar", 40.00),
                ("Pizza Pepperoni", "molho de tomate, pepperoni, queijo", 45.00),
            ])

        cursor.execute("SELECT COUNT(*) FROM cardapio_sobremesa")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
            INSERT INTO cardapio_sobremesa (nome_sobremesa, preco) VALUES (?, ?)
            ''', [
                ("Pudim", 8.00),
                ("Torta de Limão", 9.00),
                ("Quindim", 6.00),
                ("Pavê", 10.00),
            ])

        cursor.execute("SELECT COUNT(*) FROM cardapio_bebidas")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
            INSERT INTO cardapio_bebidas (nome_bebida, preco) VALUES (?, ?)
            ''', [
                ("Água", 3.00),
                ("Refri Lata", 6.00),
                ("Refri Vidro", 10.00),
                ("Jarra de Suco", 10.00),
            ])

        conn.commit()
        conn.close()








@app.route('/')
def home():
    return render_template('index.html')








@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    data = request.get_json()
    nome = data.get('nome')
    preco = data.get('preco')

    if nome and preco:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO carrinho (tipo, nome, preco) VALUES (?, ?, ?)', ('custom', nome, preco))
            conn.commit()
            return jsonify({'status': 'success', 'message': f'{nome} adicionado ao carrinho!'})
        except sqlite3.Error as e:
            return jsonify({'status': 'error', 'message': f'Erro no banco de dados: {str(e)}'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'status': 'error', 'message': 'Dados inválidos!'}), 400








@app.route('/carrinho', methods=['GET'])
def carrinho():
    conn = get_db_connection()
    cursor = conn.cursor()
    itens_carrinho = cursor.execute('SELECT * FROM carrinho').fetchall()

    detalhes_itens = []
    for item in itens_carrinho:
        detalhes_itens.append({'nome': item['nome'], 'tipo': item['tipo'], 'preco': item['preco']})

    conn.close()
    return render_template('carrinho.html', itens=detalhes_itens)








@app.route('/cadastrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        idade = request.form['idade']
        telefone = request.form['telefone']
        senha = request.form['senha']

        hashed_senha = generate_password_hash(senha)

        conn = get_db_connection()
        if conn:
            try:
                conn.execute('INSERT INTO conta (nome, email, idade, telefone, senha) VALUES (?, ?, ?, ?, ?)',
                             (nome, email, idade, telefone, hashed_senha))
                conn.commit()
                return redirect('/login')
            except sqlite3.IntegrityError:
                return "Email já cadastrado. Tente outro."
            finally:
                conn.close()

    return render_template('cadastrar.html')








@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        if not email or not senha:
            return render_template('login.html', error="Por favor, preencha todos os campos.")

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        try:
            user = conn.execute('SELECT * FROM conta WHERE email = ?', (email,)).fetchone()
            if user and check_password_hash(user['senha'], senha):
                session['user_id'] = user['id']
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Email ou senha incorretos.")
        except sqlite3.Error as e:
            return render_template('login.html', error="Erro ao acessar o banco de dados.")
        finally:
            conn.close()

    return render_template('login.html')

def usuario_logado():
    return 'user_id' in session

def verificar_login():
    if not usuario_logado():
        return redirect(url_for('login'))








@app.route('/compra', methods=['POST'])
def compra():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        itens_carrinho = cursor.execute('SELECT * FROM carrinho').fetchall()

        if not itens_carrinho:
            return jsonify({'status': 'error', 'message': 'Carrinho vazio!'}), 400

        total = sum(item['preco'] for item in itens_carrinho)

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'status': 'error', 'message': 'Usuário não está logado!'}), 403

        cursor.execute('INSERT INTO pedidos (user_id, total, data) VALUES (?, ?, datetime("now"))', (user_id, total))
        cursor.execute('DELETE FROM carrinho')
        conn.commit()

        return jsonify({'status': 'success', 'message': 'Compra finalizada com sucesso!', 'total': total})
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Erro no banco de dados: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/confirmacao', methods=['GET'])
def finalizar_compra():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Usuário não autenticado.'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        itens_carrinho = cursor.execute('SELECT nome, tipo, preco FROM carrinho').fetchall()

        detalhes_itens = [{'nome': item['nome'], 'tipo': item['tipo'], 'preco': item['preco']} for item in itens_carrinho]
        total = sum(item['preco'] for item in detalhes_itens)

        return render_template('finalizar_compra.html', itens=detalhes_itens, total=total)
    finally:
        conn.close()






if __name__ == '__main__':
    create_table()  
    app.run(debug=True)
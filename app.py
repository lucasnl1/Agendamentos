from datetime import date
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from database import connect_db, criar_tabela
import re
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2 import IntegrityError

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

# Garante que a tabela exista antes de rodar o app
connect_db()
criar_tabela()

def validar_cpf(cpf):
    """Valida se o CPF contém exatamente 11 dígitos numéricos."""
    return bool(re.fullmatch(r'\d{11}', cpf))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/agendar', methods=['POST'])
def agendar():
    try:
        cpf = request.form['cpf']
        nome = request.form['nome']
        servico = request.form['servico']
        data = request.form['data']
        hora = request.form['hora']

        # Validação do CPF
        if not validar_cpf(cpf):
            return jsonify({"erro": "CPF inválido. Deve conter 11 dígitos numéricos."}), 400

        with connect_db() as conn:
            if conn is None:
                return jsonify({"erro": "Erro ao conectar ao banco de dados."}), 500

            with conn.cursor() as cur:
                # Verifica se o CPF já tem um agendamento
                cur.execute("SELECT COUNT(*) FROM agendamentos WHERE cpf = %s", (cpf,))
                if cur.fetchone()[0] > 0:
                    return jsonify({"erro": "Este CPF já possui um agendamento!"}), 400

                # Verifica se a data e hora já estão ocupadas
                cur.execute("SELECT COUNT(*) FROM agendamentos WHERE data = %s AND hora = %s", (data, hora))
                if cur.fetchone()[0] > 0:
                    return jsonify({"erro": "Este horário já está ocupado. Escolha outro horário!"}), 400

                # Insere o agendamento se as verificações passarem
                cur.execute(
                    "INSERT INTO agendamentos (cpf, nome, servico, data, hora, status) VALUES (%s, %s, %s, %s, %s, 'Aberto')",
                    (cpf, nome, servico, data, hora)
                )
                conn.commit()

        return jsonify({"mensagem": "✅ Agendamento realizado com sucesso!"})

    except Exception as e:
        print(f"❌ Erro ao salvar no banco: {e}")
        return jsonify({"erro": f"Erro ao salvar no banco: {e}"}), 500

    
@app.route('/agendamentos')
def listar_agendamentos():
    data_str = request.args.get('data')
    status_str = request.args.get('status')
    if data_str:
        data_busca = data_str
        status_busca = status_str if status_str else 'Aberto'  # valor padrão, se desejar
    else:
        data_busca = date.today().strftime('%Y-%m-%d')
        status_busca = 'Aberto'
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT cpf, nome, data, hora, status 
            FROM agendamentos 
            WHERE data = %s 
            AND status = %s 
            ORDER BY hora
        """, (data_busca, status_busca))
        
        agendamentos = cur.fetchall()
        cur.close()
        conn.close()

        return render_template('agendamentos.html', agendamentos=agendamentos)

    except Exception as e:
        return f"Erro ao buscar agendamentos: {e}", 500

@app.route('/detalhes/<cpf>')
def detalhes_agendamento(cpf):
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT nome, servico, data, hora, status FROM agendamentos WHERE cpf = %s", (cpf,))
        agendamento = cur.fetchone()
        cur.close()
        conn.close()

        if not agendamento:
            return "Agendamento não encontrado.", 404

        return render_template('detalhes.html', agendamento=agendamento)

    except Exception as e:
        return f"Erro ao buscar detalhes: {e}", 500


@app.route('/meu_agendamento', methods=['GET', 'POST'])
def meu_agendamento():
    if request.method == 'POST':
        cpf = request.form['cpf']

        if not validar_cpf(cpf):
            return render_template('meu_agendamento.html', erro="CPF inválido! Insira um CPF com 11 dígitos numéricos.")

        try:
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("SELECT nome, servico, data, hora, status FROM agendamentos WHERE cpf = %s", (cpf,))
            agendamento = cur.fetchone()
            cur.close()
            conn.close()

            if not agendamento:
                return render_template('meu_agendamento.html', erro="Nenhum agendamento encontrado para este CPF.")

            return render_template('meu_agendamento.html', agendamento=agendamento)

        except Exception as e:
            return render_template('meu_agendamento.html', erro=f"Erro ao buscar agendamento: {e}")

    return render_template('meu_agendamento.html')


@app.route('/cancelar_agendamento', methods=['GET', 'POST'])
def cancelar_agendamento():
    mensagem = None
    erro = None

    if request.method == 'POST':
        try:
            cpf = request.form['cpf']

            if not validar_cpf(cpf):
                erro = "CPF inválido. Deve conter 11 dígitos numéricos."
                return render_template('cancelar.html', mensagem=mensagem, erro=erro)

            with connect_db() as conn:
                if conn is None:
                    erro = "Erro ao conectar ao banco de dados."
                    return render_template('cancelar.html', mensagem=mensagem, erro=erro)

                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM agendamentos WHERE cpf = %s AND status = 'Aberto'", (cpf,))
                    if cur.fetchone()[0] == 0:
                        erro = "Nenhum agendamento ativo encontrado para este CPF."
                        return render_template('cancelar.html', mensagem=mensagem, erro=erro)

                    # Deleta o agendamento para liberar CPF e horário
                    cur.execute("DELETE FROM agendamentos WHERE cpf = %s AND status = 'Aberto'", (cpf,))
                    conn.commit()
                    mensagem = "✅ Agendamento cancelado com sucesso! Você pode agendar novamente."

        except Exception as e:
            erro = f"Erro ao cancelar o agendamento: {e}"

    return render_template('cancelar.html', mensagem=mensagem, erro=erro)

@app.route('/excluir_agendamento', methods=['POST', 'GET'])
def excluir_agendamento():
    try:
        agendamento_id = request.form['id']

        with connect_db() as conn:
            if conn is None:
                return jsonify({"erro": "Erro ao conectar ao banco de dados."}), 500

            with conn.cursor() as cur:
                # Verifica se o ID do agendamento existe
                cur.execute("SELECT COUNT(*) FROM agendamentos WHERE cpf = %s", (agendamento_id,))
                if cur.fetchone()[0] == 0:
                    return jsonify({"erro": "Agendamento não encontrado!"}), 400

                # Exclui o agendamento
                cur.execute("DELETE FROM agendamentos WHERE cpf = %s", (agendamento_id,))
                conn.commit()

        return jsonify({"mensagem": "✅ Agendamento excluído com sucesso!"})

    except Exception as e:
        return jsonify({"erro": f"Erro ao excluir o agendamento: {e}"}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, senha FROM usuarios WHERE usuario = %s", (usuario,))
                user = cur.fetchone()

                if user and check_password_hash(user[1], senha):
                    session['usuario_id'] = user[0]
                    return redirect(url_for('painel'))
                else:
                    return render_template('login.html', erro="Usuário ou senha inválidos.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        if not usuario or not senha:
            flash("Todos os campos são obrigatórios!", "danger")
            return redirect(url_for('cadastro'))

        senha_hash = generate_password_hash(senha)

        with connect_db() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (usuario, senha_hash))
                    conn.commit()
                    flash("Usuário cadastrado com sucesso!", "success")
                    return redirect(url_for('cadastro'))
                except IntegrityError:  # Captura erro de chave única
                    conn.rollback()
                    flash("Usuário já cadastrado!", "danger")
                except Exception as e:
                    conn.rollback()
                    flash(f"Erro ao cadastrar usuário: {str(e)}", "danger")

    return render_template('cadastro.html')

@app.route('/agendamentos')
def painel():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, cpf, data_hora, status FROM agendamentos")
            agendamentos = cur.fetchall()

    return render_template('agendamentos.html', agendamentos=agendamentos)

# 📌 Alterar Status do Agendamento
@app.route('/alterar_status/<cpf>', methods=['POST'])
def alterar_status(cpf):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        # Retorna a página para alterar status, se necessário (ou só redireciona)
        return redirect(url_for('listar_agendamentos'))

    novo_status = ("Em execução")

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE agendamentos SET status = %s WHERE cpf = %s", (novo_status, cpf))
                conn.commit()

        flash("✅ Status atualizado com sucesso!", "success")
    except Exception as e:
        flash(f"❌ Erro ao atualizar status: {str(e)}", "danger")

    return redirect(url_for('listar_agendamentos'))

# 📌 Excluir Agendamento
@app.route('/excluir_agendamentos/<cpf>', methods=['POST'])
def excluir_agendamentos(cpf):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))  # Se não estiver logado, redireciona

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM agendamentos WHERE cpf = %s", (cpf,))
                conn.commit()

        flash("✅ Agendamento excluído com sucesso!", "success")
    
    except Exception as e:
        flash(f"Erro ao excluir o agendamento: {e}", "danger")

    return redirect(url_for('listar_agendamentos'))  # Redireciona corretamente para a lista

# 📌 Página para Gerenciar Usuários (somente para administradores)
@app.route('/usuarios')
def gerenciar_usuarios():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, usuario FROM usuarios")
            usuarios = cur.fetchall()

    return render_template('usuarios.html', usuarios=usuarios)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

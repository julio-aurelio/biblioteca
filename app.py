from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
app.secret_key = "sua_chave_secreta"

SUPABASE_URL = "https://wgmuhgcxqfyidmuftqxb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndnbXVoZ2N4cWZ5aWRtdWZ0cXhiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE5NDY1NjYsImV4cCI6MjA4NzUyMjU2Nn0.CUO3ZofxgNy1Q932Q0-poGab8JdVc1Nh-DUSLvz0RNM"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------
# FUNÇÃO AUXILIAR ULTRA OTIMIZADA
# ----------------------------
def get_livros_com_disponiveis():
    # pega todos livros e quantidade de empréstimos em 1 consulta usando join
    query = supabase.table("livros").select("*, emprestimos(id)").execute()
    livros = query.data

    for livro in livros:
        emprestimos_count = len(livro.get("emprestimos", []))
        livro["disponiveis"] = livro["total_copias"] - emprestimos_count

    return livros

# ----------------------------
# FUNÇÃO PARA TOTAIS ULTRA OTIMIZADA
# ----------------------------
def get_totais():
    livros = supabase.table("livros").select("id,total_copias,emprestimos(id)").execute().data
    total_copias = sum(l["total_copias"] for l in livros)
    total_emprestados = sum(len(l.get("emprestimos", [])) for l in livros)
    total_reservados = supabase.table("reservas").select("id").execute().count
    return total_copias, total_emprestados, total_reservados

# ----------------------------
# ROTA PRINCIPAL
# ----------------------------
@app.route("/")
def index():
    livros = get_livros_com_disponiveis()
    total_copias, total_emprestados, total_reservados = get_totais()
    return render_template(
        "index.html",
        livros=livros,
        total_copias=total_copias,
        total_emprestados=total_emprestados,
        total_reservados=total_reservados
    )

# ----------------------------
# CADASTRAR LIVRO
# ----------------------------
@app.route("/cadastrar", methods=["GET", "POST"])
def cadastrar():
    if request.method == "POST":
        titulo = request.form["titulo"].strip()
        autor = request.form["autor"].strip()
        ano = int(request.form["ano"])
        total = int(request.form["total_copias"])

        if total < 1:
            flash("O livro precisa ter pelo menos 1 cópia.", "erro")
            return redirect(url_for("cadastrar"))

        # Verifica se já existe
        existente = supabase.table("livros")\
            .select("id")\
            .eq("titulo", titulo)\
            .eq("autor", autor)\
            .eq("ano", ano)\
            .execute().data

        if existente:
            flash("Este livro já está cadastrado no sistema.", "erro")
            return redirect(url_for("index"))

        supabase.table("livros").insert({
            "titulo": titulo,
            "autor": autor,
            "ano": ano,
            "total_copias": total
        }).execute()

        flash(f"Livro '{titulo}' cadastrado com sucesso!", "sucesso")
        return redirect(url_for("index"))

    return render_template("cadastrar.html")

@app.route("/reservar/<int:livro_id>", methods=["GET", "POST"])
def reservar(livro_id):
    turmas = [
        "6ºA","6ºB","6ºC","6ºD","6ºE",
        "7ºA","7ºB","7ºC","7ºD",
        "8ºA","8ºB","8ºC",
        "9ºA","9ºB","9ºC","9ºD"
    ]

    # Pega o livro do banco
    livro = supabase.table("livros").select("*").eq("id", livro_id).single().execute().data
    if not livro:
        flash("Livro não encontrado.", "erro")
        return redirect(url_for("index"))

    # Conta empréstimos atuais (pode vir None se a consulta falhar)
    emprestimos_count = supabase.table("emprestimos")\
        .select("id").eq("livro_id", livro_id).execute().count
    if emprestimos_count is None:
        emprestimos_count = 0

    # Garantir que total_copias não seja None
    livro_total = livro.get("total_copias") or 0
    livro["disponiveis"] = livro_total - emprestimos_count

    if request.method == "POST":
        aluno = request.form["aluno"].strip()
        turma_index = int(request.form.get("turma", 1)) - 1
        turma_index = max(0, min(turma_index, len(turmas) - 1))
        turma = turmas[turma_index]

        if livro["disponiveis"] <= 0:
            # Reserva
            supabase.table("reservas").insert({
                "livro_id": livro_id,
                "aluno": aluno,
                "turma": turma,
                "data_reserva": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
            flash(f"Não há cópias disponíveis. '{livro['titulo']}' foi reservado!", "erro")
        else:
            # Empresta
            supabase.table("emprestimos").insert({
                "livro_id": livro_id,
                "aluno": aluno,
                "turma": turma,
                "data_emprestimo": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
            flash(f"Livro '{livro['titulo']}' emprestado com sucesso!", "sucesso")

        return redirect(url_for("index"))

    # GET: mostra a página de reserva
    return render_template("reservar.html", livro=livro, turmas=turmas)

# ----------------------------
# LIBERAR / DEVOLVER
# ----------------------------
@app.route("/liberar/<int:emprestimo_id>", methods=["POST"])
def liberar(emprestimo_id):
    emprestimo = supabase.table("emprestimos").select("*").eq("id", emprestimo_id).single().execute().data
    if not emprestimo:
        return redirect(url_for("index"))

    livro_id = emprestimo["livro_id"]
    supabase.table("emprestimos").delete().eq("id", emprestimo_id).execute()

    # Transferir reserva para empréstimo
    reservas = supabase.table("reservas").select("*").eq("livro_id", livro_id).order("data_reserva").limit(1).execute().data
    if reservas:
        primeira = reservas[0]
        supabase.table("emprestimos").insert({
            "livro_id": livro_id,
            "aluno": primeira["aluno"],
            "turma": primeira["turma"],
            "data_emprestimo": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        supabase.table("reservas").delete().eq("id", primeira["id"]).execute()

    return redirect(url_for("index"))

# ----------------------------
# EXCLUIR LIVRO
# ----------------------------
@app.route("/excluir/<int:livro_id>", methods=["POST"])
def excluir(livro_id):
    supabase.table("livros").delete().eq("id", livro_id).execute()
    flash("Livro excluído com sucesso!", "sucesso")
    return redirect(url_for("index"))

# ----------------------------
# ATUALIZAR LIVRO
# ----------------------------
@app.route("/atualizar/<int:livro_id>", methods=["GET", "POST"])
def atualizar(livro_id):
    livro = supabase.table("livros").select("*").eq("id", livro_id).single().execute().data
    if not livro:
        return redirect(url_for("index"))

    if request.method == "POST":
        supabase.table("livros").update({
            "titulo": request.form["titulo"],
            "autor": request.form["autor"],
            "ano": int(request.form["ano"]),
            "total_copias": int(request.form["total_copias"])
        }).eq("id", livro_id).execute()

        flash(f"Livro '{livro['titulo']}' atualizado com sucesso!", "sucesso")
        return redirect(url_for("index"))

    return render_template("atualizar.html", livro=livro)

@app.route("/buscar")
def buscar():
    termo = request.args.get("q", "").strip()

    # Busca livros filtrando título ou autor (ilike)
    livros = supabase.table("livros").select("*, emprestimos(id)")\
        .filter("titulo", "ilike", f"%{termo}%")\
        .execute().data

    # Também busca por autor e adiciona se não estiver duplicado
    livros_autor = supabase.table("livros").select("*, emprestimos(id)")\
        .filter("autor", "ilike", f"%{termo}%")\
        .execute().data

    # Evita duplicados
    ids_existentes = {livro["id"] for livro in livros}
    for l in livros_autor:
        if l["id"] not in ids_existentes:
            livros.append(l)

    # Calcula disponíveis
    for livro in livros:
        livro["disponiveis"] = livro["total_copias"] - len(livro.get("emprestimos", []))

    # Totais para o template
    total_copias = sum(l["total_copias"] for l in livros)
    total_emprestados = sum(len(l.get("emprestimos", [])) for l in livros)

    return render_template(
        "index.html",
        livros=livros,
        termo=termo,
        total_copias=total_copias,
        total_emprestados=total_emprestados
    )

@app.route("/autocomplete")
def autocomplete():
    termo = request.args.get("q", "")
    if not termo:
        return jsonify([])

    livros = supabase.table("livros").select("titulo").ilike("titulo", f"%{termo}%").limit(10).execute().data
    sugestoes = [l["titulo"] for l in livros]
    return jsonify(sugestoes)

# ----------------------------
# LISTAR EMPRESTIMOS E RESERVAS
# ----------------------------
@app.route("/reservados")
def reservados():
    livros = supabase.table("livros").select("id,total_copias").execute().data
    total_livros = sum(l["total_copias"] for l in livros)

    emprestimos = supabase.table("emprestimos").select("*, livros(*)").execute().data
    total_emprestados = len(emprestimos)

    return render_template(
        "reservados.html",
        emprestimos=emprestimos,
        total_livros=total_livros,
        total_emprestados=total_emprestados
    )

@app.route("/reservas")
def reservas():
    reservas_list = supabase.table("reservas").select("*, livros(*)").order("data_reserva").execute().data
    total_reservas = len(reservas_list)
    return render_template("reservas.html", reservas=reservas_list, total_reservas=total_reservas)

if __name__ == "__main__":
    app.run()
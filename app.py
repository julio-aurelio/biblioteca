from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os

app = Flask(__name__)
app.secret_key = "sua_chave_secreta_aqui"
ARQUIVO = "biblioteca.json"

# Funções de leitura e escrita
def carregar_livros():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_livros(livros):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(livros, f, indent=4, ensure_ascii=False)

# Verifica se o livro já existe (titulo + autor)
def livro_existe(titulo, autor, excluir_id=None):
    livros = carregar_livros()
    for i, l in enumerate(livros):
        if i == excluir_id:
            continue
        if l["titulo"].lower() == titulo.lower() and l["autor"].lower() == autor.lower():
            return True
    return False

# Página inicial - lista todos os livros
@app.route("/")
def index():
    livros = carregar_livros()
    return render_template("index.html", livros=livros)

# Lista apenas livros reservados
@app.route("/reservados")
def reservados():
    livros = [l for l in carregar_livros() if not l["disponivel"]]
    return render_template("reservados.html", livros=livros)

# Cadastrar livro
@app.route("/cadastrar", methods=["GET", "POST"])
def cadastrar():
    if request.method == "POST":
        titulo = request.form["titulo"]
        autor = request.form["autor"]
        ano = request.form["ano"]

        if livro_existe(titulo, autor):
            flash("❌ Livro já cadastrado!", "erro")  # categoria "erro"
            return redirect(url_for("cadastrar"))

        livro = {
            "titulo": titulo,
            "autor": autor,
            "ano": ano,
            "disponivel": True,
            "aluno": None,
            "turma": None
        }
        livros = carregar_livros()
        livros.append(livro)
        salvar_livros(livros)
        return redirect(url_for("index"))

    return render_template("cadastrar.html")

# Atualizar livro
@app.route("/atualizar/<int:id>", methods=["GET", "POST"])
def atualizar(id):
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livro = livros[id]

    if request.method == "POST":
        titulo = request.form["titulo"]
        autor = request.form["autor"]
        ano = request.form["ano"]

        if livro_existe(titulo, autor, excluir_id=id):
            return "Outro livro com mesmo título e autor já existe!", 400

        livro["titulo"] = titulo
        livro["autor"] = autor
        livro["ano"] = ano
        salvar_livros(livros)
        return redirect(url_for("index"))

    return render_template("atualizar.html", livro=livro, id=id)

# Reservar livro
@app.route("/reservar/<int:id>", methods=["GET", "POST"])
def reservar(id):
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livro = livros[id]

    turmas = ["6ºA","6ºB","6ºC","6ºD","6ºE","7ºA","7ºB","7ºC","7ºD",
              "8ºA","8ºB","8ºC","9ºA","9ºB","9ºC","9ºD"]

    if request.method == "POST":
        if not livro["disponivel"]:
            return "Livro já reservado!", 400
        aluno = request.form["aluno"]
        turma_index = int(request.form["turma"]) - 1
        livro["disponivel"] = False
        livro["aluno"] = aluno
        livro["turma"] = turmas[turma_index]
        salvar_livros(livros)
        return redirect(url_for("index"))

    return render_template("reservar.html", livro=livro, turmas=turmas, id=id)

# Liberar livro
@app.route("/liberar/<int:id>", methods=["GET","POST"])
def liberar(id):
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livro = livros[id]

    if request.method == "POST":
        livro["disponivel"] = True
        livro["aluno"] = None
        livro["turma"] = None
        salvar_livros(livros)
        return redirect(url_for("index"))

    return render_template("liberar.html", livro=livro, id=id)

# Excluir livro
@app.route("/excluir/<int:id>")
def excluir(id):
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livros.pop(id)
    salvar_livros(livros)
    return redirect(url_for("index"))


# Buscar livros
@app.route("/buscar", methods=["GET"])
def buscar():
    termo = request.args.get("q", "").lower()  # pega o termo da query string
    livros = carregar_livros()
    
    if termo:
        # filtra livros por título ou autor
        livros_filtrados = [
            l for l in livros
            if termo in l["titulo"].lower() or termo in l["autor"].lower()
        ]
    else:
        livros_filtrados = livros
    
    return render_template("index.html", livros=livros_filtrados, termo=termo)

@app.route("/autocomplete", methods=["GET"])
def autocomplete():
    termo = request.args.get("q", "").lower()
    livros = carregar_livros()
    resultados = []

    if termo:
        for l in livros:
            if termo in l["titulo"].lower() or termo in l["autor"].lower():
                resultados.append(l["titulo"])  # só títulos por enquanto
                if len(resultados) >= 5:  # limitar a 5 sugestões
                    break

    return jsonify(resultados)
if __name__ == "__main__":
    app.run(debug=True)
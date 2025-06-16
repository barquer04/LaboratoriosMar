from flask import Flask, request, jsonify, session, send_from_directory, render_template, redirect, url_for, Response
from flask_cors import CORS
from datetime import datetime
import json
import os
from flask_login import LoginManager, login_required, current_user, UserMixin, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from copy import deepcopy
import matplotlib.pyplot as plt
import io
import base64

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder='static')
app.secret_key = "clave_demo_segura"
CORS(app, supports_credentials=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

USUARIOS_FILE = os.path.join(BASE_DIR,  'data', 'usuarios.json')
PREGUNTAS_FILE = os.path.join(BASE_DIR, 'data', 'questions.json')
HISTORIAL_FILE = os.path.join(BASE_DIR, 'data', 'historial.json')

# ------------------------
# MODELO DE USUARIO Prueba
# ------------------------
class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    usuarios = cargar_json_usuarios(USUARIOS_FILE)
    if isinstance(usuarios, list):
        user = next((u for u in usuarios if str(u.get('id')) == str(user_id)), None)
        return User(user['id'], user['username']) if user else None
    return None

# ------------------------
# FUNCIONES DE ARCHIVOS
# ------------------------
def cargar_json_usuarios(file_path):
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

def cargar_json_historial(file_path):
    if not os.path.exists(file_path):
        return {"historial": []}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and "historial" in data:
                return data
            else:
                return {"historial": []}
    except json.JSONDecodeError:
        return {"historial": []}

def cargar_json(file_path):
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def guardar_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ------------------------
# RUTAS
# ------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/quiz')
@login_required
def quiz():
    return render_template('quiz.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', username=current_user.username)

@app.route("/data/questions.json")
def questions_json():
    return send_from_directory(os.path.join(BASE_DIR, 'data'), 'questions.json')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Faltan campos"}), 400

    usuarios = cargar_json_usuarios(USUARIOS_FILE)
    if any(u['username'] == username for u in usuarios):
        return jsonify({"error": "Usuario ya existe"}), 400

    user_id = max((u['id'] for u in usuarios), default=0) + 1
    hashed_password = generate_password_hash(password)
    usuarios.append({
        "id": user_id,
        "username": username,
        "password": hashed_password
    })
    guardar_json(USUARIOS_FILE, usuarios)

    return jsonify({"mensaje": "Usuario registrado exitosamente"}), 200

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    usuarios = cargar_json_usuarios(USUARIOS_FILE)
    user = next((u for u in usuarios if u["username"] == username), None)

    if user and check_password_hash(user["password"], password):
        login_user(User(user["id"], user["username"]))
        return jsonify({"success": True})
    return jsonify({"error": "Credenciales inválidas"}), 401

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"mensaje": "Logout exitoso"})

@app.route("/categories", methods=["GET"])
def get_categories():
    preguntas = cargar_json(PREGUNTAS_FILE)
    categorias_por_nivel = {}

    for p in preguntas:
        nivel = p.get('nivel')
        categoria = p.get('categoria')
        if nivel and categoria:
            categorias_por_nivel.setdefault(nivel, set()).add(categoria)

    return jsonify({
        "niveles": sorted(categorias_por_nivel.keys()),
        "categorias": {nivel: sorted(list(cats)) for nivel, cats in categorias_por_nivel.items()}
    })

@app.route("/questions", methods=["GET"])
def get_questions():
    nivel = request.args.get("nivel", "").strip()
    categoria = request.args.get("categoria", "").strip()

    preguntas = cargar_json(PREGUNTAS_FILE)
    filtradas = [p for p in preguntas if p.get('nivel') == nivel and p.get('categoria') == categoria]

    for p in filtradas:
        opciones = p.get('opciones', [])
        if isinstance(opciones, str):
            p['opciones'] = opciones.split('|')

    session["preguntas_actuales"] = deepcopy(filtradas)
    return jsonify({"questions": filtradas})

@app.route("/submit_answers", methods=["POST"])
@login_required
def submit_answers():
    data = request.get_json() or {}
    respuestas = data.get("respuestas", [])
    nivel = data.get("nivel", "").strip()
    categoria = data.get("categoria", "").strip()

    preguntas = cargar_json(PREGUNTAS_FILE)
    correctas_json = [p for p in preguntas if p.get('nivel') == nivel and p.get('categoria') == categoria]

    # Extraer preguntas y respuestas correctas
    preguntas_planas = correctas_json[0].get("preguntas", []) if correctas_json else []
    respuestas_correctas = [p.get("respuesta", "").strip().lower() for p in preguntas_planas]
    respuestas_usuario = [str(r).strip().lower() for r in respuestas]

    correctas = sum(
        1 for i in range(min(len(respuestas_usuario), len(respuestas_correctas)))
        if respuestas_usuario[i] == respuestas_correctas[i]
    )
    total_preguntas = len(respuestas_correctas)
    puntaje = round((correctas / total_preguntas) * 100, 2) if total_preguntas > 0 else 0

    # Construir feedback
    feedback = []
    for i in range(total_preguntas):
        pregunta = preguntas_planas[i].get("pregunta", "Pregunta no encontrada")
        respuesta_correcta = preguntas_planas[i].get("respuesta", "")
        respuesta_usuario = respuestas[i] if i < len(respuestas) else ""

        feedback.append({
            "pregunta": pregunta,
            "respuesta_correcta": respuesta_correcta,
            "respuesta_usuario": respuesta_usuario
        })

    # Guardar historial
    resultado_guardar = {
        "usuario_id": current_user.id,
        "nivel": nivel,
        "categoria": categoria,
        "puntaje": puntaje,
        "correctas": correctas,
        "total": total_preguntas,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    historial_data = cargar_json_historial(HISTORIAL_FILE)
    historial_data.setdefault("historial", []).append(resultado_guardar)
    guardar_json(HISTORIAL_FILE, historial_data)

    return jsonify({
        "success": True,
        "puntaje": puntaje,
        "correctas": correctas,
        "total": total_preguntas,
        "feedback": feedback
    })

@app.route("/history", methods=["GET"])
@login_required
def get_history():
    historial_data = cargar_json_historial(HISTORIAL_FILE)
    user_history = [
        h for h in historial_data.get("historial", [])
        if str(h.get('usuario_id')) == str(current_user.id)
    ]
    user_history.sort(key=lambda x: x.get('fecha', ''), reverse=True)
    return jsonify({"historial": user_history})

@app.route("/grafico")
@login_required
def grafico():
    # Cargar el historial de datos
    historial_data = cargar_json_historial(HISTORIAL_FILE)

    # Filtrar el historial del usuario actual
    user_history = [
        h for h in historial_data.get("historial", [])
        if str(h.get('usuario_id')) == str(current_user.id)
    ]

    # Si no hay datos de historial para el usuario
    if not user_history:
        return Response(status=204)

    # Etiquetas y puntajes para el gráfico
    labels = [f"{h['nivel']} - {h['categoria']}" for h in user_history]
    scores = [h['puntaje'] for h in user_history]

    # Crear gráfico de donut con tamaño reducido
    fig, ax = plt.subplots(figsize=(4, 4))  # más pequeño que antes

    # Gráfico de pie con estilo donut
    wedges, texts, autotexts = ax.pie(
        scores, labels=labels, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors
    )

    # Borde a las secciones
    for wedge in wedges:
        wedge.set_edgecolor('black')

    # Agujero central
    centre_circle = plt.Circle((0, 0), 0.60, color='white', fc='white', edgecolor='black')
    ax.add_artist(centre_circle)

    # Quitar ejes y ajustar forma
    ax.axis('equal')
    ax.axis('off')

    # Tamaño del texto
    plt.setp(texts, size=6)
    plt.setp(autotexts, size=5)

    # Guardar imagen sin bordes
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05)
    buf.seek(0)

    return Response(buf.getvalue(), mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True)
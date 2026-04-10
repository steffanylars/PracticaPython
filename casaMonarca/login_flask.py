"""
Modulo 2: Login con Flask (formulario HTML) + MySQL + bcrypt
MA2006B | Casa Monarca | Steffany Mishell Lara Muy | A00838589

Adapta el login original de Streamlit a una app web Flask
con persistencia en MySQL y hashing con bcrypt.

NOTA: Si no tienes MySQL instalado, cambia USA_MYSQL = False
      para usar SQLite como fallback (misma logica, distinto motor).
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt
import uuid
from datetime import datetime
from functools import wraps

# ─── SWITCH: MySQL vs SQLite (fallback) ───
USA_MYSQL = False   # Cambia a True si tienes MySQL corriendo

if USA_MYSQL:
    import mysql.connector
else:
    import sqlite3
    from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURACION
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "casa_monarca_secreto_2026"  # cambiar en produccion

ROLES = ["Admin", "Coordinador", "Operativo", "Externo"]
PERMISOS = {
    "Admin":       {"ver", "registrar", "subir", "editar", "solicitar_baja", "aprobar_baja", "gestionar_usuarios"},
    "Coordinador": {"ver", "registrar", "subir", "editar", "solicitar_baja"},
    "Operativo":   {"ver", "registrar", "subir"},
    "Externo":     set(),
}

USUARIOS_POR_DEFECTO = [
    ("admin",  "Admin123!",  "Admin",       "Carlos Mendoza"),
    ("coord1", "Coord123!",  "Coordinador", "Laura Vega"),
    ("op1",    "Oper123!",   "Operativo",   "Miguel Torres"),
    ("ext1",   "Ext1234!",   "Externo",     "Ana Garcia"),
]

# ─── Config MySQL (edita con tus credenciales) ───
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",          # tu password de MySQL
    "database": "casa_monarca",
}

# ─── Config SQLite fallback ───
SQLITE_PATH = Path(__file__).parent / "datos" / "casa_monarca_flask.db"


# ─────────────────────────────────────────────
# CAPA DE BASE DE DATOS (abstraída)
# ─────────────────────────────────────────────
def obtener_conexion():
    if USA_MYSQL:
        return mysql.connector.connect(**MYSQL_CONFIG)
    else:
        SQLITE_PATH.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(str(SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        return conn


def ejecutar(query, params=(), fetch=False, fetchone=False):
    """Helper generico para ejecutar queries."""
    conn = obtener_conexion()
    cur = conn.cursor()

    # MySQL usa %s, SQLite usa ?
    if USA_MYSQL:
        query = query.replace("?", "%s")
        # MySQL connector no soporta row_factory, usamos dictionary cursor
        cur = conn.cursor(dictionary=True)

    cur.execute(query, params)

    resultado = None
    if fetchone:
        resultado = cur.fetchone()
        if not USA_MYSQL and resultado:
            resultado = dict(resultado)
    elif fetch:
        filas = cur.fetchall()
        resultado = [dict(r) if not USA_MYSQL else r for r in filas]
    else:
        conn.commit()

    cur.close()
    conn.close()
    return resultado


def inicializar_bd():
    """Crea tablas y carga datos por defecto."""
    conn = obtener_conexion()
    cur = conn.cursor()

    if USA_MYSQL:
        # Crear la base de datos si no existe (conectar sin db primero)
        temp = mysql.connector.connect(
            host=MYSQL_CONFIG["host"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
        )
        tc = temp.cursor()
        tc.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['database']}")
        tc.close()
        temp.close()
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cur = conn.cursor()

    auto = "AUTOINCREMENT" if not USA_MYSQL else "AUTO_INCREMENT"
    text_type = "TEXT" if not USA_MYSQL else "VARCHAR(500)"
    id_type = "TEXT" if not USA_MYSQL else "VARCHAR(36)"

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS usuarios (
            id              {id_type} PRIMARY KEY,
            nombre_usuario  {text_type} UNIQUE NOT NULL,
            hash_contrasena {text_type} NOT NULL,
            rol             {text_type} NOT NULL,
            nombre          {text_type} NOT NULL,
            activo          INTEGER DEFAULT 1,
            creado_en       {text_type} NOT NULL
        )
    """)

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS log_auditoria (
            id      INTEGER PRIMARY KEY {"AUTOINCREMENT" if not USA_MYSQL else "AUTO_INCREMENT"},
            fecha   {text_type} NOT NULL,
            actor   {text_type} NOT NULL,
            accion  {text_type} NOT NULL,
            detalle {text_type} DEFAULT ''
        )
    """)

    # Usuarios por defecto
    if USA_MYSQL:
        cur.execute("SELECT COUNT(*) as cnt FROM usuarios")
        count = cur.fetchone()[0] if not isinstance(cur.fetchone(), dict) else 0
        # re-check
        cur.execute("SELECT COUNT(*) FROM usuarios")
        row = cur.fetchone()
        count = row[0] if isinstance(row, tuple) else row.get("COUNT(*)", 0)
    else:
        cur.execute("SELECT COUNT(*) FROM usuarios")
        count = cur.fetchone()[0]

    if count == 0:
        for usr, pw, rol, nombre in USUARIOS_POR_DEFECTO:
            hash_pw = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            placeholder = "?" if not USA_MYSQL else "%s"
            cur.execute(
                f"INSERT INTO usuarios (id, nombre_usuario, hash_contrasena, rol, nombre, activo, creado_en) "
                f"VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 1, {placeholder})",
                (str(uuid.uuid4()), usr, hash_pw, rol, nombre, datetime.now().isoformat()),
            )

    conn.commit()
    cur.close()
    conn.close()


# ─────────────────────────────────────────────
# FUNCIONES DE NEGOCIO
# ─────────────────────────────────────────────
def autenticar(nombre_usuario, contrasena):
    usuario = ejecutar(
        "SELECT * FROM usuarios WHERE nombre_usuario = ? AND activo = 1",
        (nombre_usuario,), fetchone=True,
    )
    if usuario and bcrypt.checkpw(contrasena.encode(), usuario["hash_contrasena"].encode()):
        return usuario
    return None


def registrar_auditoria(actor, accion, detalle=""):
    ejecutar(
        "INSERT INTO log_auditoria (fecha, actor, accion, detalle) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), actor, accion, detalle),
    )


def tiene_permiso(accion):
    rol = session.get("rol", "Externo")
    return accion in PERMISOS.get(rol, set())


def login_requerido(f):
    """Decorador: redirige a login si no hay sesion activa."""
    @wraps(f)
    def decorada(*args, **kwargs):
        if "nombre_usuario" not in session:
            flash("Inicia sesion primero.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorada


def permiso_requerido(accion):
    """Decorador: verifica permiso RBAC."""
    def decorador(f):
        @wraps(f)
        def decorada(*args, **kwargs):
            if not tiene_permiso(accion):
                flash("No tienes permisos para acceder a esta seccion.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorada
    return decorador


# ─────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    if "nombre_usuario" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre_usuario = request.form.get("nombre_usuario", "").strip()
        contrasena = request.form.get("contrasena", "").strip()

        if not nombre_usuario or not contrasena:
            flash("Completa todos los campos.", "danger")
            return render_template("login.html")

        usuario = autenticar(nombre_usuario, contrasena)
        if usuario:
            session["nombre_usuario"] = usuario["nombre_usuario"]
            session["nombre"] = usuario["nombre"]
            session["rol"] = usuario["rol"]
            registrar_auditoria(nombre_usuario, "INICIO_SESION", f"Rol: {usuario['rol']}")
            return redirect(url_for("dashboard"))
        else:
            registrar_auditoria(nombre_usuario, "INICIO_SESION_FALLIDO", "Credenciales incorrectas")
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


@app.route("/dashboard")
@login_requerido
def dashboard():
    permisos_etiquetas = {
        "ver": "Ver expedientes", "registrar": "Registrar migrante",
        "subir": "Subir documentos", "editar": "Editar expediente",
        "solicitar_baja": "Solicitar eliminacion",
        "aprobar_baja": "Aprobar eliminaciones",
        "gestionar_usuarios": "Gestionar usuarios",
    }

    log = ejecutar("SELECT * FROM log_auditoria ORDER BY id DESC LIMIT 8", fetch=True) or []

    return render_template(
        "dashboard.html",
        nombre=session["nombre"],
        rol=session["rol"],
        fecha=datetime.now().strftime("%d/%m/%Y %H:%M"),
        permisos_etiquetas=permisos_etiquetas,
        permisos_rol=PERMISOS.get(session["rol"], set()),
        tiene_permiso=tiene_permiso,
        log=log,
    )


@app.route("/usuarios")
@login_requerido
@permiso_requerido("gestionar_usuarios")
def gestion_usuarios():
    usuarios = ejecutar("SELECT * FROM usuarios", fetch=True) or []
    return render_template("usuarios.html", usuarios=usuarios, roles=ROLES,
                           tiene_permiso=tiene_permiso)


@app.route("/usuarios/crear", methods=["POST"])
@login_requerido
@permiso_requerido("gestionar_usuarios")
def crear_usuario():
    nombre = request.form.get("nombre", "").strip()
    usr = request.form.get("nombre_usuario", "").strip()
    pw = request.form.get("contrasena", "").strip()
    rol = request.form.get("rol", "Operativo")

    if not all([nombre, usr, pw]):
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("gestion_usuarios"))

    existe = ejecutar("SELECT 1 FROM usuarios WHERE nombre_usuario = ?", (usr,), fetchone=True)
    if existe:
        flash("Ese nombre de usuario ya existe.", "danger")
        return redirect(url_for("gestion_usuarios"))

    hash_pw = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    ejecutar(
        "INSERT INTO usuarios (id, nombre_usuario, hash_contrasena, rol, nombre, activo, creado_en) "
        "VALUES (?, ?, ?, ?, ?, 1, ?)",
        (str(uuid.uuid4()), usr, hash_pw, rol, nombre, datetime.now().isoformat()),
    )
    registrar_auditoria(session["nombre_usuario"], "CREAR_USUARIO", f"'{usr}' con rol {rol}")
    flash(f"Usuario '{nombre}' creado correctamente.", "success")
    return redirect(url_for("gestion_usuarios"))


@app.route("/log")
@login_requerido
@permiso_requerido("gestionar_usuarios")
def log_auditoria():
    registros = ejecutar("SELECT * FROM log_auditoria ORDER BY id DESC LIMIT 50", fetch=True) or []
    return render_template("log.html", registros=registros, tiene_permiso=tiene_permiso)


@app.route("/logout")
def logout():
    if "nombre_usuario" in session:
        registrar_auditoria(session["nombre_usuario"], "CERRAR_SESION", "")
    session.clear()
    flash("Sesion cerrada.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    inicializar_bd()
    app.run(debug=True, port=5000)

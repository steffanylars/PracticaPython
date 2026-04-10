"""
Modulo 3: Cambiar de ventana Tkinter a ruta Flask + template HTML
MA2006B | Casa Monarca | Steffany Mishell Lara Muy | A00838589

Este modulo demuestra la transicion:
  1. El usuario hace login en una ventana Tkinter (escritorio)
  2. Al autenticarse, se levanta Flask en background
  3. Se abre el dashboard en el navegador (HTML templates)

Combina login_tkinter.py (BD SQLite) con login_flask.py (rutas web).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import time
import sqlite3
import bcrypt
import uuid
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, session, redirect, url_for, request, flash

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DIRECTORIO_BASE = Path(__file__).parent
DB_PATH = DIRECTORIO_BASE / "datos" / "casa_monarca.db"
FLASK_PORT = 5050

ROLES = ["Admin", "Coordinador", "Operativo", "Externo"]
PERMISOS = {
    "Admin":       {"ver", "registrar", "subir", "editar", "solicitar_baja", "aprobar_baja", "gestionar_usuarios"},
    "Coordinador": {"ver", "registrar", "subir", "editar", "solicitar_baja"},
    "Operativo":   {"ver", "registrar", "subir"},
    "Externo":     set(),
}

USUARIOS_POR_DEFECTO = [
    {"nombre_usuario": "admin",  "contrasena": "Admin123!",  "rol": "Admin",       "nombre": "Carlos Mendoza"},
    {"nombre_usuario": "coord1", "contrasena": "Coord123!",  "rol": "Coordinador", "nombre": "Laura Vega"},
    {"nombre_usuario": "op1",    "contrasena": "Oper123!",   "rol": "Operativo",   "nombre": "Miguel Torres"},
    {"nombre_usuario": "ext1",   "contrasena": "Ext1234!",   "rol": "Externo",     "nombre": "Ana Garcia"},
]


# ─────────────────────────────────────────────
# CAPA BD (misma que login_tkinter.py)
# ─────────────────────────────────────────────
def asegurar_directorios():
    (DIRECTORIO_BASE / "datos").mkdir(exist_ok=True)


def obtener_conexion():
    asegurar_directorios()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_bd():
    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY, nombre_usuario TEXT UNIQUE NOT NULL,
            hash_contrasena TEXT NOT NULL, rol TEXT NOT NULL,
            nombre TEXT NOT NULL, activo INTEGER DEFAULT 1, creado_en TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS log_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL,
            actor TEXT NOT NULL, accion TEXT NOT NULL, detalle TEXT DEFAULT ''
        )
    """)
    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        for u in USUARIOS_POR_DEFECTO:
            h = bcrypt.hashpw(u["contrasena"].encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO usuarios VALUES (?,?,?,?,?,1,?)",
                (str(uuid.uuid4()), u["nombre_usuario"], h, u["rol"], u["nombre"],
                 datetime.now().isoformat()),
            )
    conn.commit()
    conn.close()


def autenticar_usuario(nombre_usuario, contrasena):
    conn = obtener_conexion()
    fila = conn.execute(
        "SELECT * FROM usuarios WHERE nombre_usuario = ? AND activo = 1",
        (nombre_usuario,)
    ).fetchone()
    conn.close()
    if fila and bcrypt.checkpw(contrasena.encode(), fila["hash_contrasena"].encode()):
        return dict(fila)
    return None


def registrar_auditoria(actor, accion, detalle=""):
    conn = obtener_conexion()
    conn.execute(
        "INSERT INTO log_auditoria (fecha, actor, accion, detalle) VALUES (?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), actor, accion, detalle),
    )
    conn.commit()
    conn.close()


def tiene_permiso_rol(rol, accion):
    return accion in PERMISOS.get(rol, set())


# ─────────────────────────────────────────────
# APP FLASK (se levanta en background)
# ─────────────────────────────────────────────
flask_app = Flask(__name__, template_folder=str(DIRECTORIO_BASE / "templates"))
flask_app.secret_key = "casa_monarca_bridge_2026"

# Variable compartida: el usuario autenticado desde Tkinter
_usuario_autenticado = {}


def tiene_permiso(accion):
    """Helper para templates."""
    rol = session.get("rol", "Externo")
    return accion in PERMISOS.get(rol, set())


# Inyectar tiene_permiso en todos los templates
@flask_app.context_processor
def inyectar_helpers():
    return dict(tiene_permiso=tiene_permiso)


@flask_app.route("/")
def index():
    # Auto-login con las credenciales de Tkinter
    if _usuario_autenticado and "nombre_usuario" not in session:
        session["nombre_usuario"] = _usuario_autenticado["nombre_usuario"]
        session["nombre"] = _usuario_autenticado["nombre"]
        session["rol"] = _usuario_autenticado["rol"]
    if "nombre_usuario" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_web"))


@flask_app.route("/login", methods=["GET", "POST"])
def login_web():
    """Login web por si el usuario cierra sesion y quiere re-entrar."""
    if request.method == "POST":
        usr = request.form.get("nombre_usuario", "").strip()
        pw = request.form.get("contrasena", "").strip()
        usuario = autenticar_usuario(usr, pw)
        if usuario:
            session["nombre_usuario"] = usuario["nombre_usuario"]
            session["nombre"] = usuario["nombre"]
            session["rol"] = usuario["rol"]
            registrar_auditoria(usr, "INICIO_SESION_WEB", f"Rol: {usuario['rol']}")
            return redirect(url_for("dashboard"))
        flash("Credenciales incorrectas.", "danger")
    return render_template("login.html")


@flask_app.route("/dashboard")
def dashboard():
    if "nombre_usuario" not in session:
        return redirect(url_for("login_web"))

    permisos_etiquetas = {
        "ver": "Ver expedientes", "registrar": "Registrar migrante",
        "subir": "Subir documentos", "editar": "Editar expediente",
        "solicitar_baja": "Solicitar eliminacion",
        "aprobar_baja": "Aprobar eliminaciones",
        "gestionar_usuarios": "Gestionar usuarios",
    }
    conn = obtener_conexion()
    log = [dict(r) for r in conn.execute(
        "SELECT * FROM log_auditoria ORDER BY id DESC LIMIT 8").fetchall()]
    conn.close()

    return render_template(
        "dashboard.html",
        nombre=session["nombre"], rol=session["rol"],
        fecha=datetime.now().strftime("%d/%m/%Y %H:%M"),
        permisos_etiquetas=permisos_etiquetas,
        permisos_rol=PERMISOS.get(session["rol"], set()),
        tiene_permiso=tiene_permiso, log=log,
    )


@flask_app.route("/usuarios")
def gestion_usuarios():
    if "nombre_usuario" not in session:
        return redirect(url_for("login_web"))
    conn = obtener_conexion()
    usuarios = [dict(r) for r in conn.execute("SELECT * FROM usuarios").fetchall()]
    conn.close()
    return render_template("usuarios.html", usuarios=usuarios, roles=ROLES,
                           tiene_permiso=tiene_permiso)


@flask_app.route("/usuarios/crear", methods=["POST"])
def crear_usuario():
    if "nombre_usuario" not in session:
        return redirect(url_for("login_web"))
    nombre = request.form.get("nombre", "").strip()
    usr = request.form.get("nombre_usuario", "").strip()
    pw = request.form.get("contrasena", "").strip()
    rol = request.form.get("rol", "Operativo")
    if not all([nombre, usr, pw]):
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("gestion_usuarios"))
    conn = obtener_conexion()
    if conn.execute("SELECT 1 FROM usuarios WHERE nombre_usuario = ?", (usr,)).fetchone():
        conn.close()
        flash("Usuario ya existe.", "danger")
        return redirect(url_for("gestion_usuarios"))
    h = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?,1,?)",
                 (str(uuid.uuid4()), usr, h, rol, nombre, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    registrar_auditoria(session["nombre_usuario"], "CREAR_USUARIO", f"'{usr}' rol {rol}")
    flash(f"Usuario '{nombre}' creado.", "success")
    return redirect(url_for("gestion_usuarios"))


@flask_app.route("/log")
def log_auditoria():
    if "nombre_usuario" not in session:
        return redirect(url_for("login_web"))
    conn = obtener_conexion()
    registros = [dict(r) for r in conn.execute(
        "SELECT * FROM log_auditoria ORDER BY id DESC LIMIT 50").fetchall()]
    conn.close()
    return render_template("log.html", registros=registros, tiene_permiso=tiene_permiso)


@flask_app.route("/logout")
def logout():
    if "nombre_usuario" in session:
        registrar_auditoria(session["nombre_usuario"], "CERRAR_SESION_WEB", "")
    session.clear()
    flash("Sesion cerrada.", "info")
    return redirect(url_for("login_web"))


def iniciar_flask():
    """Levanta Flask en un thread daemon (no bloquea Tkinter)."""
    flask_app.run(port=FLASK_PORT, debug=False, use_reloader=False)


# ─────────────────────────────────────────────
# VENTANA TKINTER (Login de escritorio)
# ─────────────────────────────────────────────
class VentanaLogin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Casa Monarca — Login")
        self.geometry("420x350")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")
        self._construir_ui()

    def _construir_ui(self):
        frame = tk.Frame(self, bg="white", bd=1, relief="solid")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=360, height=300)

        tk.Label(frame, text="Casa Monarca", font=("Helvetica", 18, "bold"),
                 bg="white", fg="#2c3e50").pack(pady=(20, 2))
        tk.Label(frame, text="Login de escritorio → Dashboard web",
                 font=("Helvetica", 9), bg="white", fg="#95a5a6").pack()

        ttk.Separator(frame).pack(fill="x", padx=30, pady=12)

        tk.Label(frame, text="Usuario", font=("Helvetica", 10), bg="white").pack(padx=35, anchor="w")
        self.entry_usr = tk.Entry(frame, font=("Helvetica", 11), relief="solid", bd=1)
        self.entry_usr.pack(padx=35, fill="x", ipady=3)

        tk.Label(frame, text="Contraseña", font=("Helvetica", 10), bg="white").pack(padx=35, anchor="w", pady=(8,0))
        self.entry_pw = tk.Entry(frame, font=("Helvetica", 11), relief="solid", bd=1, show="•")
        self.entry_pw.pack(padx=35, fill="x", ipady=3)
        self.entry_pw.bind("<Return>", lambda e: self._login())

        tk.Button(frame, text="Entrar y abrir Dashboard web",
                  font=("Helvetica", 10, "bold"), bg="#2980b9", fg="white",
                  relief="flat", cursor="hand2", command=self._login
                  ).pack(padx=35, fill="x", ipady=5, pady=(15, 5))

        self.lbl_error = tk.Label(frame, text="", font=("Helvetica", 9), bg="white", fg="#e74c3c")
        self.lbl_error.pack()

    def _login(self):
        global _usuario_autenticado
        usr = self.entry_usr.get().strip()
        pw = self.entry_pw.get().strip()

        if not usr or not pw:
            self.lbl_error.config(text="Completa ambos campos.")
            return

        usuario = autenticar_usuario(usr, pw)
        if not usuario:
            registrar_auditoria(usr, "LOGIN_FALLIDO_TKINTER", "")
            self.lbl_error.config(text="Credenciales incorrectas.")
            return

        # Guardar usuario para que Flask lo use
        _usuario_autenticado = usuario
        registrar_auditoria(usr, "LOGIN_TKINTER", f"Rol: {usuario['rol']} → abriendo web")

        # Levantar Flask en background
        hilo_flask = threading.Thread(target=iniciar_flask, daemon=True)
        hilo_flask.start()

        # Esperar un momento y abrir navegador
        time.sleep(1)
        webbrowser.open(f"http://localhost:{FLASK_PORT}")

        # Mostrar mensaje y cerrar ventana Tkinter
        self.lbl_error.config(text="", fg="#27ae60")
        messagebox.showinfo(
            "Sesion iniciada",
            f"Bienvenido {usuario['nombre']}.\n\n"
            f"Se abrio el dashboard en tu navegador.\n"
            f"Puedes cerrar esta ventana."
        )
        self.destroy()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    inicializar_bd()
    ventana = VentanaLogin()
    ventana.mainloop()

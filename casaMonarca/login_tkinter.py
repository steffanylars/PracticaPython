"""
Modulo 1: Login con Tkinter + SQLite
MA2006B | Casa Monarca | Steffany Mishell Lara Muy | A00838589

Adapta el login original de Streamlit a una app de escritorio
con Tkinter y persistencia en SQLite (en lugar de JSON).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import bcrypt
import uuid
import os
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURACION DE BASE DE DATOS
# ─────────────────────────────────────────────
DIRECTORIO_BASE = Path(__file__).parent
DB_PATH = DIRECTORIO_BASE / "datos" / "casa_monarca.db"

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
# CAPA DE BASE DE DATOS (SQLite)
# ─────────────────────────────────────────────
def asegurar_directorios():
    (DIRECTORIO_BASE / "datos").mkdir(exist_ok=True)


def obtener_conexion():
    """Abre conexion a SQLite. Crea tablas si no existen."""
    asegurar_directorios()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row          # acceso por nombre de columna
    conn.execute("PRAGMA journal_mode=WAL")  # mejor concurrencia
    return conn


def inicializar_bd():
    """Crea las tablas y carga usuarios por defecto si la BD esta vacia."""
    conn = obtener_conexion()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id              TEXT PRIMARY KEY,
            nombre_usuario  TEXT UNIQUE NOT NULL,
            hash_contrasena TEXT NOT NULL,
            rol             TEXT NOT NULL,
            nombre          TEXT NOT NULL,
            activo          INTEGER DEFAULT 1,
            creado_en       TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS log_auditoria (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha   TEXT NOT NULL,
            actor   TEXT NOT NULL,
            accion  TEXT NOT NULL,
            detalle TEXT DEFAULT ''
        )
    """)

    # Cargar usuarios por defecto si la tabla esta vacia
    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        for u in USUARIOS_POR_DEFECTO:
            hash_pw = bcrypt.hashpw(u["contrasena"].encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO usuarios (id, nombre_usuario, hash_contrasena, rol, nombre, activo, creado_en) "
                "VALUES (?, ?, ?, ?, ?, 1, ?)",
                (str(uuid.uuid4()), u["nombre_usuario"], hash_pw, u["rol"], u["nombre"],
                 datetime.now().isoformat()),
            )

    conn.commit()
    conn.close()


def autenticar(nombre_usuario, contrasena):
    """Devuelve dict del usuario si credenciales son validas, None si no."""
    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE nombre_usuario = ? AND activo = 1", (nombre_usuario,))
    fila = cur.fetchone()
    conn.close()

    if fila and bcrypt.checkpw(contrasena.encode(), fila["hash_contrasena"].encode()):
        return dict(fila)
    return None


def registrar_auditoria(actor, accion, detalle=""):
    conn = obtener_conexion()
    conn.execute(
        "INSERT INTO log_auditoria (fecha, actor, accion, detalle) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), actor, accion, detalle),
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# INTERFAZ GRAFICA (Tkinter)
# ─────────────────────────────────────────────
class AplicacionCasaMonarca(tk.Tk):
    """Ventana principal que maneja la navegacion entre pantallas."""

    def __init__(self):
        super().__init__()
        self.title("Casa Monarca — Sistema de Gestion Segura")
        self.geometry("800x550")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")

        self.usuario_actual = None          # se llena al hacer login

        # Contenedor donde se montan las pantallas
        self.contenedor = tk.Frame(self, bg="#f5f5f5")
        self.contenedor.pack(fill="both", expand=True)

        self.mostrar_login()

    # ---------- PANTALLA: LOGIN ----------
    def mostrar_login(self):
        self._limpiar_contenedor()

        frame = tk.Frame(self.contenedor, bg="#ffffff", bd=1, relief="solid")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=420, height=380)

        tk.Label(frame, text="Casa Monarca", font=("Helvetica", 20, "bold"),
                 bg="#ffffff", fg="#2c3e50").pack(pady=(25, 2))
        tk.Label(frame, text="Sistema de Gestion Segura de Identidades",
                 font=("Helvetica", 9), bg="#ffffff", fg="#7f8c8d").pack()

        # Separador
        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=30, pady=15)

        # Campos
        lbl_style = {"font": ("Helvetica", 10), "bg": "#ffffff", "anchor": "w"}
        entry_style = {"font": ("Helvetica", 11), "relief": "solid", "bd": 1}

        tk.Label(frame, text="Usuario", **lbl_style).pack(padx=40, fill="x")
        self.entry_usuario = tk.Entry(frame, **entry_style)
        self.entry_usuario.pack(padx=40, fill="x", ipady=4)

        tk.Label(frame, text="Contraseña", **lbl_style).pack(padx=40, fill="x", pady=(10, 0))
        self.entry_contrasena = tk.Entry(frame, show="•", **entry_style)
        self.entry_contrasena.pack(padx=40, fill="x", ipady=4)
        self.entry_contrasena.bind("<Return>", lambda e: self._intentar_login())

        # Boton
        btn_login = tk.Button(
            frame, text="Entrar", font=("Helvetica", 11, "bold"),
            bg="#2980b9", fg="white", activebackground="#3498db",
            relief="flat", cursor="hand2", command=self._intentar_login,
        )
        btn_login.pack(padx=40, fill="x", ipady=6, pady=(18, 5))

        # Nota de usuarios de prueba
        tk.Label(frame,
                 text="Prueba: admin / Admin123!  •  coord1 / Coord123!",
                 font=("Helvetica", 8), bg="#ffffff", fg="#95a5a6").pack(pady=(5, 0))
        tk.Label(frame,
                 text="op1 / Oper123!  •  ext1 / Ext1234!",
                 font=("Helvetica", 8), bg="#ffffff", fg="#95a5a6").pack()

        self.label_error = tk.Label(frame, text="", font=("Helvetica", 9),
                                    bg="#ffffff", fg="#e74c3c")
        self.label_error.pack(pady=(5, 0))

    def _intentar_login(self):
        nombre_usuario = self.entry_usuario.get().strip()
        contrasena = self.entry_contrasena.get().strip()

        if not nombre_usuario or not contrasena:
            self.label_error.config(text="Completa todos los campos.")
            return

        usuario = autenticar(nombre_usuario, contrasena)
        if usuario:
            self.usuario_actual = usuario
            registrar_auditoria(nombre_usuario, "INICIO_SESION", f"Rol: {usuario['rol']}")
            self.mostrar_dashboard()
        else:
            registrar_auditoria(nombre_usuario, "INICIO_SESION_FALLIDO", "Credenciales incorrectas")
            self.label_error.config(text="Usuario o contraseña incorrectos.")

    # ---------- PANTALLA: DASHBOARD ----------
    def mostrar_dashboard(self):
        self._limpiar_contenedor()
        u = self.usuario_actual

        # Barra superior
        barra = tk.Frame(self.contenedor, bg="#2c3e50", height=50)
        barra.pack(fill="x")
        barra.pack_propagate(False)

        tk.Label(barra, text="Casa Monarca", font=("Helvetica", 14, "bold"),
                 bg="#2c3e50", fg="white").pack(side="left", padx=15)
        tk.Label(barra, text=f"{u['nombre']}  ({u['rol']})",
                 font=("Helvetica", 10), bg="#2c3e50", fg="#bdc3c7").pack(side="left", padx=10)

        btn_salir = tk.Button(
            barra, text="Cerrar sesion", font=("Helvetica", 9),
            bg="#e74c3c", fg="white", relief="flat", cursor="hand2",
            command=self._cerrar_sesion,
        )
        btn_salir.pack(side="right", padx=15, pady=10)

        # Cuerpo
        cuerpo = tk.Frame(self.contenedor, bg="#f5f5f5")
        cuerpo.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(cuerpo, text=f"Bienvenido, {u['nombre']}",
                 font=("Helvetica", 18, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(anchor="w")
        tk.Label(cuerpo, text=f"Rol: {u['rol']}  •  {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                 font=("Helvetica", 10), bg="#f5f5f5", fg="#7f8c8d").pack(anchor="w", pady=(0, 15))

        ttk.Separator(cuerpo, orient="horizontal").pack(fill="x", pady=5)

        # Tabla de permisos
        tk.Label(cuerpo, text="Mis permisos", font=("Helvetica", 13, "bold"),
                 bg="#f5f5f5", fg="#2c3e50").pack(anchor="w", pady=(10, 5))

        columnas = ("permiso", "acceso")
        tree = ttk.Treeview(cuerpo, columns=columnas, show="headings", height=7)
        tree.heading("permiso", text="Permiso")
        tree.heading("acceso", text="Acceso")
        tree.column("permiso", width=300)
        tree.column("acceso", width=100, anchor="center")

        permisos_etiquetas = {
            "ver": "Ver expedientes", "registrar": "Registrar migrante",
            "subir": "Subir documentos", "editar": "Editar expediente",
            "solicitar_baja": "Solicitar eliminacion",
            "aprobar_baja": "Aprobar eliminaciones",
            "gestionar_usuarios": "Gestionar usuarios",
        }
        for clave, etiqueta in permisos_etiquetas.items():
            acceso = "Si" if clave in PERMISOS.get(u["rol"], set()) else "No"
            tree.insert("", "end", values=(etiqueta, acceso))

        tree.pack(fill="x")

        # Botones de navegacion (se pueden ampliar)
        frame_btns = tk.Frame(cuerpo, bg="#f5f5f5")
        frame_btns.pack(fill="x", pady=15)

        if "gestionar_usuarios" in PERMISOS.get(u["rol"], set()):
            tk.Button(frame_btns, text="Gestionar usuarios",
                      font=("Helvetica", 10), bg="#2980b9", fg="white",
                      relief="flat", cursor="hand2",
                      command=self.mostrar_gestion_usuarios).pack(side="left", padx=5)

            tk.Button(frame_btns, text="Log de auditoria",
                      font=("Helvetica", 10), bg="#8e44ad", fg="white",
                      relief="flat", cursor="hand2",
                      command=self.mostrar_log_auditoria).pack(side="left", padx=5)

    # ---------- PANTALLA: GESTION DE USUARIOS ----------
    def mostrar_gestion_usuarios(self):
        self._limpiar_contenedor()
        u = self.usuario_actual

        barra = tk.Frame(self.contenedor, bg="#2c3e50", height=50)
        barra.pack(fill="x")
        barra.pack_propagate(False)
        tk.Label(barra, text="Gestion de Usuarios", font=("Helvetica", 14, "bold"),
                 bg="#2c3e50", fg="white").pack(side="left", padx=15)
        tk.Button(barra, text="← Volver", font=("Helvetica", 9),
                  bg="#7f8c8d", fg="white", relief="flat",
                  command=self.mostrar_dashboard).pack(side="right", padx=15, pady=10)

        cuerpo = tk.Frame(self.contenedor, bg="#f5f5f5")
        cuerpo.pack(fill="both", expand=True, padx=30, pady=15)

        # Lista de usuarios
        conn = obtener_conexion()
        usuarios = [dict(r) for r in conn.execute("SELECT * FROM usuarios").fetchall()]
        conn.close()

        columnas = ("nombre", "usuario", "rol", "activo")
        tree = ttk.Treeview(cuerpo, columns=columnas, show="headings", height=6)
        tree.heading("nombre", text="Nombre")
        tree.heading("usuario", text="Usuario")
        tree.heading("rol", text="Rol")
        tree.heading("activo", text="Activo")
        tree.column("nombre", width=200)
        tree.column("usuario", width=150)
        tree.column("rol", width=120)
        tree.column("activo", width=80, anchor="center")

        for usr in usuarios:
            tree.insert("", "end", values=(
                usr["nombre"], usr["nombre_usuario"],
                usr["rol"], "Si" if usr["activo"] else "No"))
        tree.pack(fill="x", pady=(0, 15))

        # Formulario para nuevo usuario
        ttk.Separator(cuerpo).pack(fill="x", pady=5)
        tk.Label(cuerpo, text="Crear nuevo usuario", font=("Helvetica", 12, "bold"),
                 bg="#f5f5f5").pack(anchor="w", pady=(10, 5))

        form = tk.Frame(cuerpo, bg="#f5f5f5")
        form.pack(fill="x")

        tk.Label(form, text="Nombre:", bg="#f5f5f5").grid(row=0, column=0, sticky="w", pady=3)
        entry_nombre = tk.Entry(form, width=30)
        entry_nombre.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Usuario:", bg="#f5f5f5").grid(row=1, column=0, sticky="w", pady=3)
        entry_usr = tk.Entry(form, width=30)
        entry_usr.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Contraseña:", bg="#f5f5f5").grid(row=2, column=0, sticky="w", pady=3)
        entry_pw = tk.Entry(form, width=30, show="•")
        entry_pw.grid(row=2, column=1, padx=5, pady=3)

        tk.Label(form, text="Rol:", bg="#f5f5f5").grid(row=3, column=0, sticky="w", pady=3)
        combo_rol = ttk.Combobox(form, values=ROLES, state="readonly", width=27)
        combo_rol.set("Operativo")
        combo_rol.grid(row=3, column=1, padx=5, pady=3)

        def crear():
            n, usr_id, pw, rol = (entry_nombre.get().strip(), entry_usr.get().strip(),
                                  entry_pw.get().strip(), combo_rol.get())
            if not all([n, usr_id, pw]):
                messagebox.showerror("Error", "Todos los campos son obligatorios.")
                return
            conn = obtener_conexion()
            existe = conn.execute("SELECT 1 FROM usuarios WHERE nombre_usuario = ?", (usr_id,)).fetchone()
            if existe:
                conn.close()
                messagebox.showerror("Error", "Ese nombre de usuario ya existe.")
                return
            hash_pw = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO usuarios (id, nombre_usuario, hash_contrasena, rol, nombre, activo, creado_en) "
                "VALUES (?, ?, ?, ?, ?, 1, ?)",
                (str(uuid.uuid4()), usr_id, hash_pw, rol, n, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()
            registrar_auditoria(u["nombre_usuario"], "CREAR_USUARIO", f"'{usr_id}' con rol {rol}")
            messagebox.showinfo("Exito", f"Usuario '{n}' creado.")
            self.mostrar_gestion_usuarios()  # refrescar

        tk.Button(form, text="Crear usuario", bg="#27ae60", fg="white",
                  relief="flat", cursor="hand2", command=crear).grid(
            row=4, column=1, sticky="e", padx=5, pady=10)

    # ---------- PANTALLA: LOG AUDITORIA ----------
    def mostrar_log_auditoria(self):
        self._limpiar_contenedor()

        barra = tk.Frame(self.contenedor, bg="#2c3e50", height=50)
        barra.pack(fill="x")
        barra.pack_propagate(False)
        tk.Label(barra, text="Log de Auditoria", font=("Helvetica", 14, "bold"),
                 bg="#2c3e50", fg="white").pack(side="left", padx=15)
        tk.Button(barra, text="← Volver", font=("Helvetica", 9),
                  bg="#7f8c8d", fg="white", relief="flat",
                  command=self.mostrar_dashboard).pack(side="right", padx=15, pady=10)

        cuerpo = tk.Frame(self.contenedor, bg="#f5f5f5")
        cuerpo.pack(fill="both", expand=True, padx=20, pady=15)

        conn = obtener_conexion()
        registros = conn.execute("SELECT fecha, actor, accion, detalle FROM log_auditoria ORDER BY id DESC LIMIT 50").fetchall()
        conn.close()

        columnas = ("fecha", "actor", "accion", "detalle")
        tree = ttk.Treeview(cuerpo, columns=columnas, show="headings", height=18)
        tree.heading("fecha", text="Fecha")
        tree.heading("actor", text="Actor")
        tree.heading("accion", text="Accion")
        tree.heading("detalle", text="Detalle")
        tree.column("fecha", width=150)
        tree.column("actor", width=100)
        tree.column("accion", width=180)
        tree.column("detalle", width=300)

        for r in registros:
            tree.insert("", "end", values=(r["fecha"], r["actor"], r["accion"], r["detalle"]))

        scrollbar = ttk.Scrollbar(cuerpo, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ---------- UTILIDADES ----------
    def _limpiar_contenedor(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

    def _cerrar_sesion(self):
        registrar_auditoria(self.usuario_actual["nombre_usuario"], "CERRAR_SESION", "")
        self.usuario_actual = None
        self.mostrar_login()


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    inicializar_bd()
    app = AplicacionCasaMonarca()
    app.mainloop()

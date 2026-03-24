"""
Casa Monarca – Modulo de Login, Gestion de Usuarios y Doble Control
MA2006B | Steffany Mishell Lara Muy | A00838589
"""

import streamlit as st
import json
import bcrypt
import uuid
from datetime import datetime
from pathlib import Path


# ARCHIVOS JSON

DIRECTORIO_BASE      = Path(__file__).parent
ARCHIVO_USUARIOS     = DIRECTORIO_BASE / "datos" / "usuarios.json"
ARCHIVO_LOG          = DIRECTORIO_BASE / "datos" / "log_auditoria.json"
ARCHIVO_SOLICITUDES  = DIRECTORIO_BASE / "datos" / "solicitudes_eliminacion.json"
ARCHIVO_EXPEDIENTES  = DIRECTORIO_BASE / "datos" / "expedientes.json"


# ROLES Y PERMISOS (RBAC)

ROLES = ["Admin", "Coordinador", "Operativo", "Externo"]

PERMISOS = {
    "Admin":        {"ver", "registrar", "subir", "editar", "solicitar_baja", "aprobar_baja", "gestionar_usuarios"},
    "Coordinador":  {"ver", "registrar", "subir", "editar", "solicitar_baja"},
    "Operativo":    {"ver", "registrar", "subir"},
    "Externo":      set(),
}

USUARIOS_POR_DEFECTO = [
    {"nombre_usuario": "admin",  "contrasena": "Admin123!",  "rol": "Admin",       "nombre": "Carlos Mendoza"},
    {"nombre_usuario": "coord1", "contrasena": "Coord123!",  "rol": "Coordinador", "nombre": "Laura Vega"},
    {"nombre_usuario": "op1",    "contrasena": "Oper123!",   "rol": "Operativo",   "nombre": "Miguel Torres"},
    {"nombre_usuario": "ext1",   "contrasena": "Ext1234!",   "rol": "Externo",     "nombre": "Ana Garcia"},
]

EXPEDIENTES_POR_DEFECTO = [
    {"id": "EXP-001", "nombre": "Juan Lopez Ramirez",    "pais": "Honduras",    "estatus": "Activo"},
    {"id": "EXP-002", "nombre": "Maria Perez Gomez",     "pais": "Guatemala",   "estatus": "Activo"},
    {"id": "EXP-003", "nombre": "Pedro Hernandez Silva", "pais": "El Salvador", "estatus": "Activo"},
]


# HELPERS DE PERSISTENCIA

def asegurar_directorios():
    (DIRECTORIO_BASE / "datos").mkdir(exist_ok=True)

def cargar_json(ruta, valor_defecto):
    asegurar_directorios()
    if not ruta.exists():
        guardar_json(ruta, valor_defecto)
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_json(ruta, datos):
    asegurar_directorios()
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def cargar_usuarios():
    datos = cargar_json(ARCHIVO_USUARIOS, [])
    if not datos:
        usuarios = []
        for u in USUARIOS_POR_DEFECTO:
            hash_contrasena = bcrypt.hashpw(u["contrasena"].encode(), bcrypt.gensalt()).decode()
            usuarios.append({
                "id":              str(uuid.uuid4()),
                "nombre_usuario":  u["nombre_usuario"],
                "hash_contrasena": hash_contrasena,
                "rol":             u["rol"],
                "nombre":          u["nombre"],
                "activo":          True,
                "creado_en":       datetime.now().isoformat(),
            })
        guardar_json(ARCHIVO_USUARIOS, usuarios)
        return usuarios
    return datos

def guardar_usuarios(usuarios):        guardar_json(ARCHIVO_USUARIOS, usuarios)
def cargar_log():                      return cargar_json(ARCHIVO_LOG, [])
def guardar_log(log):                  guardar_json(ARCHIVO_LOG, log)
def cargar_solicitudes():              return cargar_json(ARCHIVO_SOLICITUDES, [])
def guardar_solicitudes(solicitudes):  guardar_json(ARCHIVO_SOLICITUDES, solicitudes)
def cargar_expedientes():              return cargar_json(ARCHIVO_EXPEDIENTES, EXPEDIENTES_POR_DEFECTO)
def guardar_expedientes(exps):         guardar_json(ARCHIVO_EXPEDIENTES, exps)


# AUDITORIA

def registrar_auditoria(actor, accion, detalle=""):
    log = cargar_log()
    log.append({
        "fecha":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor":   actor,
        "accion":  accion,
        "detalle": detalle,
    })
    guardar_log(log)


# AUTENTICACION

def autenticar(nombre_usuario, contrasena):
    usuarios = cargar_usuarios()
    for u in usuarios:
        if u["nombre_usuario"] == nombre_usuario and u["activo"]:
            if bcrypt.checkpw(contrasena.encode(), u["hash_contrasena"].encode()):
                return u
    return None

def tiene_permiso(accion):
    rol = st.session_state.get("usuario", {}).get("rol", "Externo")
    return accion in PERMISOS.get(rol, set())


# PANTALLA: INICIO DE SESION

def pantalla_login():
    st.title("Casa Monarca")
    st.subheader("Sistema de Gestion Segura de Identidades")
    st.divider()

    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        st.markdown("**Iniciar sesion**")
        nombre_usuario = st.text_input("Usuario")
        contrasena     = st.text_input("Contrasena", type="password")

        if st.button("Entrar", use_container_width=True):
            if not nombre_usuario or not contrasena:
                st.error("Completa todos los campos.")
            else:
                usuario = autenticar(nombre_usuario, contrasena)
                if usuario:
                    st.session_state["usuario"] = usuario
                    registrar_auditoria(usuario["nombre_usuario"], "INICIO_SESION", f"Rol: {usuario['rol']}")
                    st.rerun()
                else:
                    registrar_auditoria(nombre_usuario, "INICIO_SESION_FALLIDO", "Credenciales incorrectas")
                    st.error("Usuario o contrasena incorrectos.")

    with col_der:
        st.markdown("**Usuarios de prueba**")
        st.table({
            "Usuario":    ["admin", "coord1", "op1", "ext1"],
            "Contrasena": ["Admin123!", "Coord123!", "Oper123!", "Ext1234!"],
            "Rol":        ["Admin", "Coordinador", "Operativo", "Externo"],
        })


# PANTALLA: INICIO / DASHBOARD

def pantalla_inicio():
    usuario = st.session_state["usuario"]

    st.title(f"Bienvenido, {usuario['nombre']}")
    st.caption(f"Rol: {usuario['rol']}  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.divider()

    st.subheader("Mis permisos")
    todos_los_permisos = {
        "ver":                "Ver expedientes",
        "registrar":          "Registrar migrante",
        "subir":              "Subir documentos",
        "editar":             "Editar expediente",
        "solicitar_baja":     "Solicitar eliminacion",
        "aprobar_baja":       "Aprobar eliminaciones",
        "gestionar_usuarios": "Gestionar usuarios",
    }
    st.table({
        "Permiso": list(todos_los_permisos.values()),
        "Acceso":  ["Si" if p in PERMISOS[usuario["rol"]] else "No" for p in todos_los_permisos],
    })

    st.subheader("Actividad reciente")
    log = cargar_log()[-8:][::-1]
    if log:
        st.table(log)
    else:
        st.info("Sin actividad registrada.")


# PANTALLA: GESTION DE USUARIOS

def pantalla_gestion_usuarios():
    actor = st.session_state["usuario"]["nombre_usuario"]

    if not tiene_permiso("gestionar_usuarios"):
        st.error("No tienes permisos para gestionar usuarios.")
        return

    st.title("Gestion de Usuarios")

    pestana_lista, pestana_nuevo, pestana_editar = st.tabs(["Listado", "Nuevo usuario", "Editar / Desactivar"])

    with pestana_lista:
        usuarios = cargar_usuarios()
        st.table({
            "Nombre":  [u["nombre"] for u in usuarios],
            "Usuario": [u["nombre_usuario"] for u in usuarios],
            "Rol":     [u["rol"] for u in usuarios],
            "Activo":  ["Si" if u["activo"] else "No" for u in usuarios],
            "Creado":  [u.get("creado_en", "")[:10] for u in usuarios],
        })

    with pestana_nuevo:
        nombre     = st.text_input("Nombre completo", key="nuevo_nombre")
        usuario_id = st.text_input("Nombre de usuario (unico)", key="nuevo_usuario")
        contrasena = st.text_input("Contrasena inicial", type="password", key="nuevo_pass")
        rol        = st.selectbox("Rol", ROLES, key="nuevo_rol")

        if st.button("Crear usuario"):
            if not all([nombre, usuario_id, contrasena]):
                st.error("Todos los campos son obligatorios.")
            else:
                usuarios = cargar_usuarios()
                if any(u["nombre_usuario"] == usuario_id for u in usuarios):
                    st.error("Ese nombre de usuario ya existe.")
                else:
                    hash_contrasena = bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()
                    usuarios.append({
                        "id":              str(uuid.uuid4()),
                        "nombre_usuario":  usuario_id,
                        "hash_contrasena": hash_contrasena,
                        "rol":             rol,
                        "nombre":          nombre,
                        "activo":          True,
                        "creado_en":       datetime.now().isoformat(),
                    })
                    guardar_usuarios(usuarios)
                    registrar_auditoria(actor, "CREAR_USUARIO", f"'{usuario_id}' creado con rol {rol}")
                    st.success(f"Usuario {nombre} creado correctamente.")
                    st.rerun()

    with pestana_editar:
        usuarios = cargar_usuarios()
        opciones = [u["nombre_usuario"] for u in usuarios if u["nombre_usuario"] != actor]

        if not opciones:
            st.info("No hay otros usuarios para editar.")
        else:
            seleccionado = st.selectbox("Selecciona usuario", opciones, key="editar_sel")
            objetivo     = next(u for u in usuarios if u["nombre_usuario"] == seleccionado)

            nuevo_nombre = st.text_input("Nombre completo",   value=objetivo["nombre"],           key="editar_nombre")
            nuevo_rol    = st.selectbox("Rol", ROLES,          index=ROLES.index(objetivo["rol"]), key="editar_rol")
            nuevo_activo = st.checkbox("Cuenta activa",        value=objetivo["activo"],           key="editar_activo")
            nueva_pass   = st.text_input("Nueva contrasena (dejar vacio = sin cambio)", type="password", key="editar_pass")

            if st.button("Guardar cambios"):
                for u in usuarios:
                    if u["nombre_usuario"] == seleccionado:
                        rol_anterior = u["rol"]
                        u["nombre"]  = nuevo_nombre
                        u["rol"]     = nuevo_rol
                        u["activo"]  = nuevo_activo
                        if nueva_pass:
                            u["hash_contrasena"] = bcrypt.hashpw(nueva_pass.encode(), bcrypt.gensalt()).decode()
                        break
                guardar_usuarios(usuarios)
                registrar_auditoria(actor, "EDITAR_USUARIO",
                    f"'{seleccionado}': nombre={nuevo_nombre}, rol {rol_anterior}->{nuevo_rol}, activo={nuevo_activo}")
                st.success("Usuario actualizado.")
                st.rerun()


# PANTALLA: SOLICITAR ELIMINACION (DOBLE CONTROL)

def pantalla_solicitar_eliminacion():
    actor = st.session_state["usuario"]

    if not tiene_permiso("solicitar_baja"):
        st.error("No tienes permisos para solicitar eliminaciones.")
        return

    st.title("Solicitar eliminacion de expediente")
    st.info("Principio de doble control activo: tu solicitud debe ser aprobada por un administrador distinto a ti.")

    expedientes = cargar_expedientes()
    activos     = [e for e in expedientes if e.get("estatus") == "Activo"]

    if not activos:
        st.warning("No hay expedientes activos disponibles.")
        return

    opciones     = {f"{e['id']} - {e['nombre']}": e["id"] for e in activos}
    etiqueta_sel = st.selectbox("Expediente a eliminar", list(opciones.keys()))
    motivo       = st.text_area("Motivo de eliminacion")

    if st.button("Enviar solicitud"):
        if not motivo.strip():
            st.error("El motivo es obligatorio.")
        else:
            id_expediente = opciones[etiqueta_sel]
            solicitudes   = cargar_solicitudes()
            ya_existe     = any(
                s["id_expediente"] == id_expediente and s["estatus"] == "Pendiente"
                for s in solicitudes
            )
            if ya_existe:
                st.warning("Ya existe una solicitud pendiente para ese expediente.")
            else:
                solicitudes.append({
                    "id":                 str(uuid.uuid4()),
                    "id_expediente":      id_expediente,
                    "etiqueta":           etiqueta_sel,
                    "solicitado_por":     actor["nombre_usuario"],
                    "nombre_solicitante": actor["nombre"],
                    "motivo":             motivo,
                    "estatus":            "Pendiente",
                    "solicitado_en":      datetime.now().isoformat(),
                    "resuelto_por":       None,
                    "resuelto_en":        None,
                })
                guardar_solicitudes(solicitudes)
                registrar_auditoria(actor["nombre_usuario"], "SOLICITAR_ELIMINACION",
                    f"Expediente {id_expediente} - motivo: {motivo[:60]}")
                st.success("Solicitud enviada. Un administrador debe aprobarla.")


# PANTALLA: APROBAR / RECHAZAR ELIMINACIONES

def pantalla_aprobar_eliminaciones():
    actor = st.session_state["usuario"]

    if not tiene_permiso("aprobar_baja"):
        st.error("Solo los administradores pueden aprobar eliminaciones.")
        return

    st.title("Aprobar eliminaciones")
    st.caption("Solo puedes aprobar solicitudes de otros usuarios, no las tuyas propias.")

    solicitudes = cargar_solicitudes()
    pendientes  = [s for s in solicitudes if s["estatus"] == "Pendiente" and s["solicitado_por"] != actor["nombre_usuario"]]
    propias     = [s for s in solicitudes if s["estatus"] == "Pendiente" and s["solicitado_por"] == actor["nombre_usuario"]]

    if propias:
        st.warning(f"Tienes {len(propias)} solicitud(es) propias pendientes. Otro administrador debe aprobarlas.")

    if not pendientes:
        st.info("No hay solicitudes pendientes de otros usuarios.")
    else:
        for s in pendientes:
            with st.expander(f"{s['etiqueta']} — solicitado por {s['nombre_solicitante']}"):
                st.write(f"**Expediente:** {s['etiqueta']}")
                st.write(f"**Solicitante:** {s['nombre_solicitante']} (@{s['solicitado_por']})")
                st.write(f"**Motivo:** {s['motivo']}")
                st.write(f"**Fecha:** {s['solicitado_en'][:19].replace('T', ' ')}")

                col_apr, col_rec = st.columns(2)

                with col_apr:
                    if st.button("Aprobar", key=f"aprobar_{s['id']}"):
                        expedientes = cargar_expedientes()
                        for e in expedientes:
                            if e["id"] == s["id_expediente"]:
                                e["estatus"] = "Eliminado"
                                break
                        guardar_expedientes(expedientes)

                        for sol in solicitudes:
                            if sol["id"] == s["id"]:
                                sol["estatus"]      = "Aprobada"
                                sol["resuelto_por"] = actor["nombre_usuario"]
                                sol["resuelto_en"]  = datetime.now().isoformat()
                                break
                        guardar_solicitudes(solicitudes)
                        registrar_auditoria(actor["nombre_usuario"], "APROBAR_ELIMINACION",
                            f"Expediente {s['id_expediente']} eliminado. Solicitado por @{s['solicitado_por']}")
                        st.success("Solicitud aprobada. Expediente eliminado.")
                        st.rerun()

                with col_rec:
                    if st.button("Rechazar", key=f"rechazar_{s['id']}"):
                        for sol in solicitudes:
                            if sol["id"] == s["id"]:
                                sol["estatus"]      = "Rechazada"
                                sol["resuelto_por"] = actor["nombre_usuario"]
                                sol["resuelto_en"]  = datetime.now().isoformat()
                                break
                        guardar_solicitudes(solicitudes)
                        registrar_auditoria(actor["nombre_usuario"], "RECHAZAR_ELIMINACION",
                            f"Solicitud de @{s['solicitado_por']} sobre {s['id_expediente']} rechazada")
                        st.warning("Solicitud rechazada.")
                        st.rerun()

    st.divider()
    st.subheader("Historial de solicitudes resueltas")
    resueltas = [s for s in solicitudes if s["estatus"] != "Pendiente"][::-1]
    if resueltas:
        st.table({
            "Expediente":       [s["etiqueta"] for s in resueltas],
            "Solicitado por":   [s["solicitado_por"] for s in resueltas],
            "Estatus":          [s["estatus"] for s in resueltas],
            "Resuelto por":     [s.get("resuelto_por", "") for s in resueltas],
            "Fecha resolucion": [str(s.get("resuelto_en", ""))[:10] for s in resueltas],
        })
    else:
        st.info("Sin historial aun.")


# PANTALLA: EXPEDIENTES (MOCK)

def pantalla_expedientes():
    if not tiene_permiso("ver"):
        st.error("No tienes permisos para ver expedientes.")
        return

    st.title("Expedientes")
    st.caption("Vista de prueba. Los datos reales son gestionados por los modulos de Andres y Maria Paula.")

    expedientes = cargar_expedientes()
    st.table({
        "ID":      [e["id"] for e in expedientes],
        "Nombre":  [e["nombre"] for e in expedientes],
        "Pais":    [e["pais"] for e in expedientes],
        "Estatus": [e["estatus"] for e in expedientes],
    })


# PANTALLA: LOG DE AUDITORIA

def pantalla_log_auditoria():
    if not tiene_permiso("gestionar_usuarios"):
        st.error("Acceso restringido a administradores.")
        return

    st.title("Log de Auditoria")
    log = cargar_log()[::-1]
    if not log:
        st.info("El log esta vacio.")
    else:
        st.table(log)


# PANTALLA: MI PERFIL

def pantalla_perfil():
    usuario = st.session_state["usuario"]
    actor   = usuario["nombre_usuario"]

    st.title("Mi perfil")
    st.write(f"**Usuario:** {usuario['nombre_usuario']}")
    st.write(f"**Rol:** {usuario['rol']}")
    st.divider()

    st.subheader("Actualizar nombre visible")
    nuevo_nombre = st.text_input("Nombre completo", value=usuario["nombre"])
    nueva_pass   = st.text_input("Nueva contrasena (dejar vacio = sin cambio)", type="password")

    if st.button("Guardar cambios"):
        usuarios = cargar_usuarios()
        for u in usuarios:
            if u["nombre_usuario"] == actor:
                u["nombre"] = nuevo_nombre
                if nueva_pass:
                    u["hash_contrasena"] = bcrypt.hashpw(nueva_pass.encode(), bcrypt.gensalt()).decode()
                break
        guardar_usuarios(usuarios)
        st.session_state["usuario"]["nombre"] = nuevo_nombre
        registrar_auditoria(actor, "ACTUALIZAR_PERFIL", f"Nombre actualizado a '{nuevo_nombre}'")
        st.success("Perfil actualizado.")
        st.rerun()


# BARRA LATERAL + NAVEGACION

def barra_lateral():
    usuario = st.session_state["usuario"]

    with st.sidebar:
        st.title("Casa Monarca")
        st.write(f"**{usuario['nombre']}**")
        st.write(f"Rol: {usuario['rol']}")
        st.divider()

        paginas = [("Inicio", "inicio")]

        if tiene_permiso("ver"):
            paginas.append(("Expedientes", "expedientes"))
        if tiene_permiso("solicitar_baja"):
            paginas.append(("Solicitar eliminacion", "solicitar_eliminacion"))
        if tiene_permiso("aprobar_baja"):
            paginas.append(("Aprobar eliminaciones", "aprobar_eliminaciones"))
        if tiene_permiso("gestionar_usuarios"):
            paginas.append(("Gestionar usuarios", "gestion_usuarios"))
            paginas.append(("Log de auditoria", "log_auditoria"))

        paginas.append(("Mi perfil", "perfil"))

        for etiqueta, clave in paginas:
            if st.button(etiqueta, key=f"nav_{clave}", use_container_width=True):
                st.session_state["pagina"] = clave
                st.rerun()

        st.divider()
        if st.button("Cerrar sesion", use_container_width=True):
            registrar_auditoria(usuario["nombre_usuario"], "CERRAR_SESION", "")
            st.session_state.clear()
            st.rerun()

    return st.session_state.get("pagina", "inicio")


# MAIN

def main():
    st.set_page_config(
        page_title="Casa Monarca",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "usuario" not in st.session_state:
        pantalla_login()
        return

    pagina = barra_lateral()

    rutas = {
        "inicio":                pantalla_inicio,
        "expedientes":           pantalla_expedientes,
        "solicitar_eliminacion": pantalla_solicitar_eliminacion,
        "aprobar_eliminaciones": pantalla_aprobar_eliminaciones,
        "gestion_usuarios":      pantalla_gestion_usuarios,
        "log_auditoria":         pantalla_log_auditoria,
        "perfil":                pantalla_perfil,
    }

    rutas.get(pagina, pantalla_inicio)()


if __name__ == "__main__":
    main()
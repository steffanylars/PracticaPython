# app.py
import time
import datetime as dt

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt


# ----------------------------
# Config
# ----------------------------
st.set_page_config(page_title="Para mi Dieguisss", layout="centered")

TARGET_NAME = "Diego José Roca Rodríguez"
TARGET_DOB = dt.date(2003, 5, 15)


# ----------------------------
# Helpers
# ----------------------------
def heart_curve(k: float, n: int = 2500):
    # Domain for sqrt(3 - x^2) requires |x| <= sqrt(3)
    x = np.linspace(-np.sqrt(3), np.sqrt(3), n)
    base = np.abs(x) ** (2 / 3)
    ripple = 0.9 * np.sin(k * x) * np.sqrt(np.maximum(0.0, 3 - x**2))
    y = base + ripple
    return x, y


def plot_with_glow(x, y, k: float):
    fig, ax = plt.subplots(figsize=(6, 7), dpi=150)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    # Glow: draw multiple strokes behind the main line
    for lw, a in [(10, 0.05), (8, 0.07), (6, 0.10), (4, 0.14)]:
        ax.plot(x, y, linewidth=lw, alpha=a, color='red')

    ax.plot(x, y, linewidth=1.8, color='red')

    ax.set_xlim(-2, 2)
    ax.set_ylim(-1.6, 2.6)

    # Axes styling
    for spine in ax.spines.values():
        spine.set_color((1, 1, 1, 0.25))

    ax.tick_params(colors=(1, 1, 1, 0.65), labelsize=9)
    ax.axhline(0, color=(1, 1, 1, 0.25), linewidth=1)
    ax.axvline(0, color=(1, 1, 1, 0.25), linewidth=1)

    ax.set_title("Te amo mi dieguisss <3", pad=14, fontsize=14, color=(1, 1, 1, 0.90))
    ax.text(
        0.5, -0.10, f"k = {k:.2f}",
        transform=ax.transAxes,
        ha="center", va="top",
        color=(1, 1, 1, 0.70),
        fontsize=10
    )

    return fig


# ----------------------------
# State
# ----------------------------
if "validated" not in st.session_state:
    st.session_state.validated = False


# ----------------------------
# Gate (first: nothing else appears)
# ----------------------------
st.markdown("### Acceso")
name = st.text_input("Nombre completo", value="")
dob = st.date_input("Fecha de nacimiento", value=dt.date(2003, 5, 15), format="DD/MM/YYYY")

col1, col2 = st.columns(2)
with col1:
    if st.button("Entrar", use_container_width=True):
        st.session_state.validated = (name == TARGET_NAME and dob == TARGET_DOB)

with col2:
    if st.button("Reiniciar", use_container_width=True):
        st.session_state.validated = False
        st.rerun()


if not st.session_state.validated:
    if name or dob:
        if (name != TARGET_NAME) or (dob != TARGET_DOB):
            st.error("¿Qué haces en mi programa??? fuchilaaaaaa!!!!")
    st.stop()


# ----------------------------
# Approved view: glow + graph + k from 0..50
# ----------------------------
st.markdown("---")
st.markdown("### Gráfica")

st.latex(r"""
y = x^{\frac{2}{3}} + 0.9 \sin(kx)\sqrt{3 - x^2}
""")

st.latex(r"""
|x| \leq \sqrt{3}
""")

c1, c2 = st.columns(2)

with c2:
    k = st.slider(
        "k",
        min_value=0.0,
        max_value=50.0,
        value=33.71,
        step=0.01
    )

placeholder = st.empty()

# Initial "brillo" effect moment: show a quick glow pulse once per run
if "glow_pulse_done" not in st.session_state:
    st.session_state.glow_pulse_done = False

if not st.session_state.glow_pulse_done:
    x0, y0 = heart_curve(k)
    for a in [0.02, 0.05, 0.09, 0.14]:
        fig, ax = plt.subplots(figsize=(6, 7), dpi=150)
        fig.patch.set_facecolor("black")
        ax.set_facecolor("black")
        ax.plot(x0, y0, linewidth=10, alpha=a, color='red')
        ax.plot(x0, y0, linewidth=1.8, color='red')
        ax.set_xlim(-2, 2)
        ax.set_ylim(-1.6, 2.6)
        ax.axis("off")
        placeholder.pyplot(fig, clear_figure=True)
        time.sleep(0.02)
    st.session_state.glow_pulse_done = True

# Normal plot
x, y = heart_curve(k)
fig = plot_with_glow(x, y, k)
placeholder.pyplot(fig, clear_figure=True)

# Animation controls
with c1:
    animate = st.button("Animar k de 0 a 50", use_container_width=True)

speed = 40  # Default speed in ms

if animate:
    for kk in np.linspace(0, 50, 151):
        x, y = heart_curve(float(kk))
        fig = plot_with_glow(x, y, float(kk))
        placeholder.pyplot(fig, clear_figure=True)
        time.sleep(speed / 1000.0)
# <3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3 LIBRERÍAS

import streamlit as st
import sympy as sp
import pandas as pd
from sympy import diff
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

# Símbolo global

x = sp.symbols(‘x’)

# Transformaciones que permiten: 2x, 0.2x, 3sin(x), x^2, etc.

TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)

def parse_ecuacion(s):
return parse_expr(s, transformations=TRANSFORMS, local_dict={“x”: x})

# <3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3 INTERFAZ

st.title(“Métodos Numéricos”)
st.write(“A00838589 - Steffany Mishell Lara Muy”)
st.write(“Escribe tu polinomio. Algunos puntos a tomar en cuenta:”)
st.markdown(”””

- El número $e$ se escribe como `exp`. Ej: `exp(x)` para $e^x$.
- Ya puedes usar **multiplicación implícita**: `2x`, `0.2x`, `3sin(x)` funcionan.
- Para potencias usa `x**2` o `x^2`.
- La variable independiente siempre es `x`.
- Si dejas $x_0$ vacío, se usará $(a+b)/2$.
  “””)

ecuacion_str = st.text_input(“Ingresa tu ecuación:”, value=“x**2 - 4*x + 3”)

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)
with col1:
a = st.number_input(“a”, min_value=-10000.0, max_value=10000.0, value=-5.0, step=0.01)
with col2:
b = st.number_input(“b”, min_value=-10000.0, max_value=10000.0, value=5.0, step=0.01)
with col3:
cantIter = st.number_input(“Iteraciones”, min_value=1, value=10, step=1)
with col4:
x0 = st.number_input(“x0”, value=(a + b) / 2)
with col5:
alfa = st.number_input(“Alfa (Descenso)”, value=0.05, step=0.01)
with col6:
ffib = st.number_input(“Cant. F. Fibonacci”, min_value=3, value=10, step=1)

objetivo = st.selectbox(“Selecciona el objetivo”, (“Minimizar”, “Maximizar”))

# <3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3 ERRORES

@st.dialog(“Error”)
def mostrar_error(msg):
st.write(msg)

# <3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3 MÉTODOS NUMÉRICOS

def descenso(ecuacion, x0, alfa, cantIter, objetivo):
“”“Descenso/ascenso por gradiente.”””
gradiente = sp.diff(ecuacion, x)
signo = -1 if objetivo == “Minimizar” else 1
xi = float(x0)
for _ in range(int(cantIter)):
xi = xi + signo * float(alfa) * float(gradiente.subs(x, xi))
return xi

def metodoFibonacci(ecuacion, ffib, a, b, objetivo, cantIter):
“”“Búsqueda de Fibonacci.”””
n = int(ffib)
fib = [0, 1]
for i in range(2, n + 1):
fib.append(fib[i - 1] + fib[i - 2])

```
a, b = float(a), float(b)
iters = min(int(cantIter), n - 2)
for _ in range(iters):
    x1 = a + (fib[n - 2] / fib[n]) * (b - a)
    x2 = a + (fib[n - 1] / fib[n]) * (b - a)
    y1 = float(ecuacion.subs(x, x1))
    y2 = float(ecuacion.subs(x, x2))

    if objetivo == "Minimizar":
        if y1 < y2:
            b = x2
        else:
            a = x1
    else:  # Maximizar
        if y1 > y2:
            b = x2
        else:
            a = x1
    n -= 1
return (a + b) / 2
```

def razonDorada(ecuacion, a, b, cantIter, objetivo):
“”“Búsqueda de razón dorada.”””
fi = (5 ** 0.5 - 1) / 2
a, b = float(a), float(b)
for _ in range(int(cantIter)):
x1 = b - fi * (b - a)
x2 = a + fi * (b - a)
y1 = float(ecuacion.subs(x, x1))
y2 = float(ecuacion.subs(x, x2))
if objetivo == “Minimizar”:
if y1 < y2:
b = x2
else:
a = x1
else:
if y1 > y2:
b = x2
else:
a = x1
return (a + b) / 2

def newtonRaphson(ecuacion, x0, cantIter):
“”“Newton-Raphson sobre f’(x)=0 para optimizar.”””
d1 = sp.diff(ecuacion, x)
d2 = sp.diff(d1, x)
xi = float(x0)
for _ in range(int(cantIter)):
d2_val = float(d2.subs(x, xi))
if d2_val == 0:
break
xi = xi - float(d1.subs(x, xi)) / d2_val
return xi

def interpolacionCuadratica(ecuacion, a, b, cantIter, objetivo):
“”“Interpolación cuadrática.”””
x1, x2, x3 = float(a), (float(a) + float(b)) / 2, float(b)
for _ in range(int(cantIter)):
y1 = float(ecuacion.subs(x, x1))
y2 = float(ecuacion.subs(x, x2))
y3 = float(ecuacion.subs(x, x3))

```
    num = y1 * (x2**2 - x3**2) + y2 * (x3**2 - x1**2) + y3 * (x1**2 - x2**2)
    den = y1 * (x2 - x3) + y2 * (x3 - x1) + y3 * (x1 - x2)
    if den == 0:
        break
    x4 = 0.5 * num / den
    y4 = float(ecuacion.subs(x, x4))

    puntos = sorted([(x1, y1), (x2, y2), (x3, y3), (x4, y4)], key=lambda p: p[1])
    if objetivo == "Minimizar":
        mejores = puntos[:3]
    else:
        mejores = puntos[-3:]
    mejores = sorted(mejores, key=lambda p: p[0])
    x1, x2, x3 = mejores[0][0], mejores[1][0], mejores[2][0]
return x2
```

def errorPorcentual(listaX, teorico):
“”“Error % vs valor teórico ya filtrado por tipo (min/max).”””
if teorico is None:
return [None] * len(listaX)
errores = []
for xi in listaX:
if teorico == 0:
errores.append(abs(xi - teorico))
else:
errores.append(abs((xi - teorico) / teorico) * 100)
return errores

# <3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3<3 EJECUCIÓN

if st.button(“Ver ecuación”):
if not ecuacion_str:
mostrar_error(“Escribe una ecuación.”)
elif b <= a:
mostrar_error(“El límite superior b debe ser mayor que a.”)
else:
try:
ecuacion = parse_ecuacion(ecuacion_str)
st.latex(rf”f(x) = {sp.latex(ecuacion)}, \quad x \in [{a}, {b}]”)
except Exception:
mostrar_error(“No pude interpretar la ecuación. Revisa la sintaxis.”)

if st.button(“Métodos Numéricos”):
try:
ecuacion = parse_ecuacion(ecuacion_str)
except Exception:
mostrar_error(“No pude interpretar la ecuación.”)
st.stop()

```
if b <= a:
    mostrar_error("El límite superior b debe ser mayor que a.")
    st.stop()

resultados = {
    "Descenso": descenso(ecuacion, x0, alfa, cantIter, objetivo),
    "Fibonacci": metodoFibonacci(ecuacion, ffib, a, b, objetivo, cantIter),
    "Razón Dorada": razonDorada(ecuacion, a, b, cantIter, objetivo),
    "Newton Raphson": newtonRaphson(ecuacion, x0, cantIter),
    "Interpolación Cuadrática": interpolacionCuadratica(ecuacion, a, b, cantIter, objetivo),
}

# Valor teórico: punto crítico que coincida con el objetivo (min o max)
teorico = None
try:
    d1 = sp.diff(ecuacion, x)
    d2 = sp.diff(d1, x)
    criticos = sp.solve(d1, x)
    criticos = [float(c) for c in criticos if c.is_real]
    if objetivo == "Minimizar":
        criticos = [c for c in criticos if float(d2.subs(x, c)) > 0]
    else:
        criticos = [c for c in criticos if float(d2.subs(x, c)) < 0]
    criticos = [c for c in criticos if float(a) <= c <= float(b)]

    if criticos:
        promedio = sum(resultados.values()) / len(resultados)
        teorico = min(criticos, key=lambda c: abs(c - promedio))
except Exception:
    pass

# Fallback numérico: si no se encontró teórico analítico (función trascendente),
# hacer un barrido denso sobre [a,b] y refinarlo con Brent.
if teorico is None:
    try:
        import numpy as np
        f_lamb = sp.lambdify(x, ecuacion, "numpy")
        xs_grid = np.linspace(float(a), float(b), 5000)
        ys_grid = f_lamb(xs_grid)
        if objetivo == "Minimizar":
            idx = int(np.argmin(ys_grid))
        else:
            idx = int(np.argmax(ys_grid))
        teorico = float(xs_grid[idx])

        # Refinamiento opcional con Newton-Raphson sobre f'(x)=0
        try:
            d1 = sp.diff(ecuacion, x)
            d2 = sp.diff(d1, x)
            xi = teorico
            for _ in range(50):
                d1v = float(d1.subs(x, xi))
                d2v = float(d2.subs(x, xi))
                if d2v == 0 or abs(d1v) < 1e-12:
                    break
                xi_new = xi - d1v / d2v
                if not (float(a) <= xi_new <= float(b)):
                    break
                if abs(xi_new - xi) < 1e-12:
                    xi = xi_new
                    break
                xi = xi_new
            teorico = xi
        except Exception:
            pass
    except Exception:
        teorico = None

errores = errorPorcentual(list(resultados.values()), teorico)

df = pd.DataFrame(
    {
        "Xn": list(resultados.values()),
        "Valor Teórico": [teorico] * len(resultados),
        "Error %": errores,
    },
    index=list(resultados.keys()),
)
st.table(df)

# ----------- Gráfica
import numpy as np
import plotly.graph_objects as go

f_lamb = sp.lambdify(x, ecuacion, "numpy")
xs = np.linspace(float(a), float(b), 400)
try:
    ys = f_lamb(xs)
except Exception:
    ys = np.array([float(ecuacion.subs(x, xi)) for xi in xs])

fig = go.Figure()
fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="f(x)", line=dict(color="#a78bfa", width=2)))

colores = {
    "Descenso": "#60a5fa",
    "Fibonacci": "#f472b6",
    "Razón Dorada": "#fbbf24",
    "Newton Raphson": "#34d399",
    "Interpolación Cuadrática": "#f87171",
}
for nombre, xi in resultados.items():
    yi = float(ecuacion.subs(x, xi))
    fig.add_trace(go.Scatter(
        x=[xi], y=[yi], mode="markers", name=nombre,
        marker=dict(size=12, color=colores[nombre], line=dict(width=1, color="white")),
    ))

if teorico is not None:
    yt = float(ecuacion.subs(x, teorico))
    fig.add_trace(go.Scatter(
        x=[teorico], y=[yt], mode="markers", name="Teórico",
        marker=dict(size=14, symbol="star", color="white", line=dict(width=1, color="black")),
    ))

fig.update_layout(
    title="f(x) y aproximaciones por método",
    xaxis_title="x", yaxis_title="f(x)",
    template="plotly_dark", height=500,
)
st.plotly_chart(fig, use_container_width=True)
```
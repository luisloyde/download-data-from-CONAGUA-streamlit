import streamlit as st
import requests
import urllib3
import pandas as pd
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -------------------------
# Catálogo de estados
# -------------------------
ESTADO_NOMBRE_A_CLAVE = {
    "aguascalientes": "ags",
    "baja california": "bc",
    "baja california sur": "bcs",
    "campeche": "camp",
    "coahuila": "coah",
    "colima": "col",
    "chiapas": "chis",
    "chihuahua": "chih",
    "cdmx": "df",
    "durango": "dgo",
    "guanajuato": "gto",
    "guerrero": "gro",
    "hidalgo": "hgo",
    "jalisco": "jal",
    "estado de méxico": "mex",
    "michoacan": "mich",
    "morelos": "mor",
    "nayarit": "nay",
    "nuevo león": "nl",
    "oaxaca": "oax",
    "puebla": "pue",
    "querétaro": "qro",
    "quintana roo": "qroo",
    "san luis potosí": "slp",
    "sinaloa": "sin",
    "sonora": "son",
    "tabasco": "tab",
    "tamaulipas": "tamps",
    "tlaxcala": "tlax",
    "veracruz": "ver",
    "yucatán": "yuc",
    "zacatecas": "zac"
}

# -------------------------
# Funciones principales
# -------------------------

@st.cache_data(show_spinner=False)
def descargar_data_cache(nombre_estado, clave):
    """
    Descarga la data de CONAGUA y la cachea
    """
    estado = ESTADO_NOMBRE_A_CLAVE.get(nombre_estado.lower())
    clave = str(clave).zfill(5)
    base = "https://smn.conagua.gob.mx/tools/RESOURCES/Normales_Climatologicas"
    url = f"{base}/Mensuales/{estado}/mes{clave}.txt"

    r = requests.get(url, verify=False)
    if r.status_code == 200 and len(r.text) > 50:
        return r.text
    return None

def estacion_operando(texto):
    return any("SITUACIÓN" in l and "OPERANDO" in l.upper() for l in texto.splitlines())

def parsear_lluvia_regex(texto, anio_min=1980, min_meses=9):
    """
    Parseo rápido usando regex
    """
    # Patrón: Año ... Lluvia_mm ... Meses
    pattern = r"(\d{4})\s+.*?(\d+\.?\d*)\s+\d+\s+(\d+)"
    registros = [
        {"Año": int(a), "Lluvia máxima 24h (mm)": float(lluvia), "Meses con dato": int(meses)}
        for a, lluvia, meses in re.findall(pattern, texto)
        if int(a) >= anio_min and int(meses) >= min_meses
    ]
    df = pd.DataFrame(registros)
    if not df.empty:
        df = df.sort_values("Lluvia máxima 24h (mm)", ascending=False)
        df["Rank"] = range(1, len(df) + 1)
    return df

def validar_min_anios(df, min_anios=40):
    return df["Año"].nunique() >= min_anios, df["Año"].nunique()

# -------------------------
# Interfaz Streamlit
# -------------------------
st.title("Normales Climatológicas – Lluvia Máxima 24h")

estado = st.selectbox("Estado", sorted(ESTADO_NOMBRE_A_CLAVE.keys()))
clave = st.text_input("Clave de estación (5 dígitos)", "")
anio_min = st.number_input("Año mínimo", 1950, 2025, 1980)
min_meses = st.slider("Meses mínimos con dato", 1, 12, 9)
min_anios = st.number_input("Años mínimos requeridos", 10, 100, 40)

if st.button("Procesar estación"):
    if not clave.strip():
        st.warning("Introduce la clave de estación")
        st.stop()

    with st.spinner("Descargando información..."):
        contenido = descargar_data_cache(estado, clave)

    if contenido is None:
        st.error(f"La estación {clave} no existe o no tiene datos mensuales en {estado}")
        st.stop()

    st.success("Datos descargados")

    if not estacion_operando(contenido):
        st.error("La estación NO está operando")
        st.stop()
    else:
        st.success("Estación operando")

    df_lluvia = parsear_lluvia_regex(contenido, anio_min=anio_min, min_meses=min_meses)

    if df_lluvia.empty:
        st.warning("No hay años con cobertura suficiente")
        st.stop()

    es_valida, n_anios = validar_min_anios(df_lluvia, min_anios)
    if not es_valida:
        st.error(f"La estación sólo tiene {n_anios} años válidos (< {min_anios})")
    else:
        st.success(f"Estación válida con {n_anios} años")
        st.subheader("Ranking de lluvia máxima 24 h")
        st.dataframe(df_lluvia.head(50), use_container_width=True)  # Muestra solo primeras 50 filas

        csv_bytes = df_lluvia.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar CSV",
            csv_bytes,
            file_name=f"lluvia_max_24h_{estado}_{clave}.csv",
            mime="text/csv"
        )

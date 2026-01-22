import streamlit as st
import requests
import urllib3
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def descargar_data(nombre_estado, clave):
    
    # Colocar estado en mismo formato
    estado = ESTADO_NOMBRE_A_CLAVE.get(nombre_estado.lower())

    # Normalizar clave a 5 dígitos
    clave = str(clave).zfill(5)

    # Construcción de URL
    base = "https://smn.conagua.gob.mx/tools/RESOURCES/Normales_Climatologicas"
    TIPO = "Mensuales"
    PREF = "mes"
    url = f"{base}/{TIPO}/{estado}/{PREF}{clave}.txt"
    
    # Solicitud de data
    r = requests.get(url, verify=False)

    # Comprobación de existencia de data y return
    if r.status_code == 200 and len(r.text) > 50:
        return {
            "ok": True,
            "estado": nombre_estado,
            "estado_clave": estado,
            "clave_estacion": clave,
            "tipo": TIPO,
            "url": url,
            "contenido": r.text
        }
    else:
        return {
            "ok": False,
            "estado": nombre_estado,
            "estado_clave": estado,
            "clave_estacion": clave,
            "tipo": TIPO,
            "url": url,
            "mensaje": f"La estación {clave} no existe o no tiene datos mensuales en {nombre_estado}"
        }

def estacion_operando(texto):
    for linea in texto.splitlines():
        if "SITUACIÓN" in linea:
            return "OPERANDO" in linea.upper()
    return False

def extraer_bloque_lluvia_maxima(texto):
    lineas = texto.splitlines()
    inicio = None

    for i, l in enumerate(lineas):
        if l.strip() == "LLUVIA MÁXIMA 24 H.":
            inicio = i + 2
            break

    if inicio is None:
        return []

    datos = []
    for l in lineas[inicio:]:
        if l.strip() == "" or not l.strip()[0].isdigit():
            break
        datos.append(l)

    return datos

def parsear_lluvia_maxima(texto, anio_min=1980, min_meses=9):
    filas = extraer_bloque_lluvia_maxima(texto)
    registros = []

    for fila in filas:
        cols = fila.split()
        try:
            anio = int(cols[0])
            acum = float(cols[-3])
            meses = int(cols[-1])
        except:
            continue

        if anio < anio_min or meses < min_meses:
            continue

        registros.append({
            "Año": anio,
            "Lluvia máxima 24h (mm)": acum,
            "Meses con dato": meses
        })

    df = pd.DataFrame(registros)

    if not df.empty:
        df = df.sort_values("Lluvia máxima 24h (mm)", ascending=False)
        df["Rank"] = range(1, len(df) + 1)

    return df

def validar_min_anios(df, min_anios=40):
    return df["Año"].nunique() >= min_anios, df["Año"].nunique()

st.title("Normales Climatológicas – Lluvia Máxima 24h")

estado = st.selectbox(
    "Estado",
    sorted(ESTADO_NOMBRE_A_CLAVE.keys())
)

clave = st.text_input(
    "Clave de estación (5 dígitos)",
    ""
)

anio_min = st.number_input("Año mínimo", 1950, 2025, 1980)
min_meses = st.slider("Meses mínimos con dato", 1, 12, 9)
min_anios = st.number_input("Años mínimos requeridos", 10, 100, 40)

if st.button("Procesar estación"):

    if clave.strip() == "":
        st.warning("Introduce la clave de estación")
        st.stop()

    with st.spinner("Descargando información..."):
        res = descargar_data(estado, clave)

    if not res["ok"]:
        st.error(res["mensaje"])
        st.stop()

    st.success("Datos descargados")

    if not estacion_operando(res["contenido"]):
        st.error("La estación NO está operando")
        st.stop()
    else:
        st.success("Estación operando")

    df_lluvia = parsear_lluvia_maxima(
        res["contenido"],
        anio_min=anio_min,
        min_meses=min_meses
    )

    if df_lluvia.empty:
        st.warning("No hay años con cobertura suficiente")
        st.stop()

    es_valida, n_anios = validar_min_anios(df_lluvia, min_anios)

    if not es_valida:
        st.error(f"La estación sólo tiene {n_anios} años válidos (< {min_anios})")
    else:
        st.success(f"Estación válida con {n_anios} años")

        st.subheader("Ranking de lluvia máxima 24 h")
        st.dataframe(df_lluvia, use_container_width=True)

        st.download_button(
            "Descargar CSV",
            df_lluvia.to_csv(index=False),
            file_name=f"lluvia_max_24h_{estado}_{clave}.csv",
            mime="text/csv"
        )

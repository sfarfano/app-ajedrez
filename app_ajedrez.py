import streamlit as st
import pandas as pd
from datetime import datetime, date
import os
import yagmail
from fpdf import FPDF
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE")
EMAIL_CONTRASENA = os.getenv("EMAIL_CONTRASENA")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")

archivo_excel = "alumnos_ajedrez.xlsx"

if not os.path.exists(archivo_excel):
    df = pd.DataFrame(columns=[
        "Nombre", "RUT", "Fecha Nacimiento", "Curso", "Colegio/Club",
        "ELO Nacional", "ELO FIDE", "Sección", "Valor Clase", "Valor Mensual",
        "Clases por Semana", "Teléfono", "Correo", "Correo Apoderado", "Fecha Inicio"
    ])
    df.to_excel(archivo_excel, index=False)

df = pd.read_excel(archivo_excel)

st.set_page_config(page_title="Ajedrez Alumnos", layout="wide")
st.image("logo chess.jpg", width=200)
st.title("🎓 Registro de Alumnos de Ajedrez")
menu = st.sidebar.radio("Menú", ["Historial de Clases", 
    "Registrar Alumno", "Listado de Alumnos", "Registrar Asistencia",
    "Registrar Pago", "Ver Morosos", "Resumen Mensual PDF", "Estado de Pago Alumno"])


secciones = sorted(df["Sección"].dropna().astype(str).unique())
cursos = sorted(df["Curso"].dropna().astype(str).unique())
seccion_sel = st.sidebar.selectbox("Filtrar por Sección", ["Todas"] + secciones)
curso_sel = st.sidebar.selectbox("Filtrar por Curso", ["Todos"] + cursos)

def filtrar(df):
    if seccion_sel != "Todas":
        df = df[df["Sección"] == seccion_sel]
    if curso_sel != "Todos":
        df = df[df["Curso"] == curso_sel]
    return df

if menu == "Historial de Clases":
    st.subheader("📚 Historial de Clases Registradas")
    asistencias = []
    with pd.ExcelFile(archivo_excel) as xls:
        for hoja in xls.sheet_names:
            if hoja.startswith("Asistencia_"):
                df_asis = pd.read_excel(xls, sheet_name=hoja)
                df_asis["Fecha"] = hoja.replace("Asistencia_", "").replace("_", "-")
                asistencias.append(df_asis)

    if asistencias:
        historial = pd.concat(asistencias)
        historial = historial.merge(df[["RUT", "Nombre"]], on="RUT", how="left")
        st.dataframe(historial[["Fecha", "Nombre", "Estado", "Observación"]].sort_values(by=["Fecha", "Nombre"]))
    else:
        st.warning("No hay registros de asistencia aún.")

# --- REGISTRAR ALUMNO ---
# Incluye campo 'Valor Mensual'
if menu == "Registrar Alumno":
    st.subheader("📝 Ingresar nuevo alumno")
    with st.form("form_alumno"):
        nombre = st.text_input("Nombre Completo")
        rut = st.text_input("RUT")
        nacimiento = st.date_input("Fecha de Nacimiento", min_value=date(1950, 1, 1))
        curso = st.text_input("Curso")
        club = st.text_input("Colegio o Club")
        elo_nat = st.number_input("ELO Nacional", step=1, value=0)
        elo_fide = st.number_input("ELO FIDE", step=1, value=0)
        seccion = st.text_input("Sección")
        valor_clase = st.number_input("Valor por Clase ($)", step=1000, value=25000)
        valor_mensual = st.number_input("Valor Mensual ($)", step=1000, value=100000)
        clases_semana = st.number_input("Clases por semana", min_value=1, max_value=7, value=1)
        correo_apoderado = st.text_input("Correo del Apoderado")
        telefono = st.text_input("Teléfono")
        correo = st.text_input("Correo Electrónico")
        fecha_inicio = st.date_input("Fecha de Inicio del Curso", value=date.today())
        guardar = st.form_submit_button("Guardar")

        if guardar:
            nuevo = pd.DataFrame([{
                "Nombre": nombre, "RUT": rut, "Fecha Nacimiento": nacimiento,
                "Curso": curso, "Colegio/Club": club, "ELO Nacional": elo_nat,
                "ELO FIDE": elo_fide, "Sección": seccion, "Valor Clase": valor_clase,
                "Valor Mensual": valor_mensual,
                "Clases por Semana": clases_semana,
                "Correo Apoderado": correo_apoderado,
                "Teléfono": telefono, "Correo": correo,
                "Fecha Inicio": fecha_inicio
            }])
            df = pd.concat([df, nuevo], ignore_index=True)
            df.to_excel(archivo_excel, index=False)
            st.success("✅ Alumno guardado correctamente.")

# --- REGISTRAR ASISTENCIA ---
elif menu == "Registrar Asistencia":
    st.subheader("📆 Registrar Asistencia por Fecha")
    alumno_sel = st.selectbox("Selecciona un alumno", df["Nombre"].unique())
    df_filtrado = df[df["Nombre"] == alumno_sel]
    fecha = st.date_input("Selecciona la fecha", value=date.today(), format="DD/MM/YYYY")
    
    asistencias = {}
    observaciones = {}
    for i, row in df_filtrado.iterrows():
        st.markdown("---")
        estado = st.selectbox(f"{row['Nombre']} - Estado", ["Asistente", "Inasistente", "Retirado"], key=f"asis_{i}")
        obs = st.text_input(f"Observación clase {row['Nombre']}", key=f"obs_{i}")
        asistencias[row["RUT"]] = estado
        observaciones[row["RUT"]] = obs

    if st.button("Guardar Asistencia"):
        hoja = f"Asistencia_{fecha.strftime('%Y_%m_%d')}"
        with pd.ExcelWriter(archivo_excel, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
            pd.DataFrame([
                {"RUT": k, "Estado": asistencias[k], "Observación": observaciones[k]} for k in asistencias
            ]).to_excel(writer, sheet_name=hoja, index=False)
        st.success("Asistencia guardada.")

# --- LISTADO DE ALUMNOS ---
# Eliminación de alumno corregida con st.rerun
elif menu == "Listado de Alumnos":
    df_filtrado = df.copy()
    st.subheader("📋 Listado de Alumnos")
    
    for i, row in df_filtrado.iterrows():
        with st.expander(f"{row['Nombre']} ({row['RUT']})"):
            nombre = st.text_input("Nombre", row['Nombre'], key=f"n_{i}")
            curso = st.text_input("Curso", row['Curso'], key=f"c_{i}")
            seccion = st.text_input("Sección", row['Sección'], key=f"s_{i}")
            telefono = st.text_input("Teléfono", row.get('Teléfono', ''), key=f"t_{i}")
            correo = st.text_input("Correo", row.get('Correo', ''), key=f"e_{i}")
            valor_default = int(row['Valor Clase']) if pd.notnull(row['Valor Clase']) else 25000
            valor = st.number_input("Valor Clase", value=valor_default, key=f"v_{i}")
            mensual_default = int(row['Valor Mensual']) if 'Valor Mensual' in row and pd.notnull(row['Valor Mensual']) else 100000
            valor_mensual = st.number_input("Valor Mensual", value=mensual_default, key=f"vm_{i}")
            clases_sem = int(row['Clases por Semana']) if 'Clases por Semana' in row and pd.notnull(row['Clases por Semana']) else 1
            clases_semana = st.number_input("Clases por Semana", value=clases_sem, key=f"cl_{i}")
            correo_apod = st.text_input("Correo del Apoderado", row.get('Correo Apoderado', ''), key=f"ca_{i}")
            guardar = st.button("Guardar cambios", key=f"g_{i}")
            eliminar = st.button("Eliminar alumno", key=f"del_{i}")

            if guardar:
                df.at[i, "Nombre"] = nombre
                df.at[i, "Curso"] = curso
                df.at[i, "Sección"] = seccion
                df.at[i, "Teléfono"] = telefono
                df.at[i, "Correo"] = correo
                df.at[i, "Valor Clase"] = valor
                df.at[i, "Valor Mensual"] = valor_mensual
                df.at[i, "Clases por Semana"] = clases_semana
                df.at[i, "Correo Apoderado"] = correo_apod
                df.to_excel(archivo_excel, index=False)
                st.success("Cambios guardados.")

            if eliminar:
                df = df.drop(index=i).reset_index(drop=True)
                df.to_excel(archivo_excel, index=False)
                st.warning("Alumno eliminado.")
                st.rerun()

# --- REGISTRAR PAGO ---
elif menu == "Registrar Pago":
    st.subheader("💵 Registrar Pago")
    alumno_sel_pago = st.selectbox("Selecciona un alumno", df["Nombre"].unique())
    df_filtrado = df[df["Nombre"] == alumno_sel_pago]
    mes_actual = datetime.now().strftime("%m-%Y")
    
    pagos = {}
    for i, row in df_filtrado.iterrows():
        monto = st.number_input(f"Pago de {row['Nombre']} ($)", min_value=0, step=1000, key=f"pago_{i}")
        pagos[row["RUT"]] = monto

    fecha_pago = st.date_input("Fecha de pago recibido", value=date.today())

    if st.button("Guardar Pagos"):
        hoja = f"Pagos_{mes_actual}"
        with pd.ExcelWriter(archivo_excel, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
            pd.DataFrame([{"RUT": k, "Monto Pagado": v, "Fecha Pago": fecha_pago} for k, v in pagos.items()]).to_excel(writer, sheet_name=hoja, index=False)
        st.success("Pagos guardados.")

# --- VER MOROSOS ---
elif menu == "Ver Morosos":
    st.subheader("🚨 Alumnos Morosos")
    mes = datetime.now().strftime("%m-%Y")

    try:
        pagos = pd.read_excel(archivo_excel, sheet_name=f"Pagos_{mes}")
    except:
        pagos = pd.DataFrame(columns=["RUT", "Monto Pagado"])

    df_filtrado = filtrar(df.copy())
    df_filtrado["Pagado"] = df_filtrado["RUT"].apply(lambda rut: pagos[pagos["RUT"] == rut]["Monto Pagado"].sum())
    df_filtrado["Clases Plan"] = df_filtrado["Clases por Semana"] * 4
    df_filtrado["Esperado"] = df_filtrado["Clases Plan"] * df_filtrado["Valor Clase"]
    df_filtrado["Deuda"] = df_filtrado["Esperado"] - df_filtrado["Pagado"]

    morosos = df_filtrado[df_filtrado["Deuda"] > 0]
    st.dataframe(morosos[["Nombre", "Curso", "Sección", "Esperado", "Pagado", "Deuda"]])

# --- ESTADO DE PAGO INDIVIDUAL ---
elif menu == "Estado de Pago Alumno":
    mes = datetime.now().strftime("%m-%Y")
    st.subheader("📤 Estado de Pago por Alumno")
    alumno_estado = st.selectbox("Selecciona un alumno", df["Nombre"].unique())
    rut = df[df["Nombre"] == alumno_estado]["RUT"].values[0]

    try:
        pagos = pd.read_excel(archivo_excel, sheet_name=f"Pagos_{mes}")
    except:
        pagos = pd.DataFrame(columns=["RUT", "Monto Pagado"])

    asistencias = []
    with pd.ExcelFile(archivo_excel) as xls:
        for hoja in xls.sheet_names:
            if hoja.startswith("Asistencia_") and mes in hoja:
                asistencias.append(pd.read_excel(xls, sheet_name=hoja))

    if asistencias:
        df_asis = pd.concat(asistencias)
        asistidas = df_asis[df_asis["RUT"] == rut]
        clases_asistidas = asistidas[asistidas["Estado"] == "Asistente"].shape[0]
    else:
        clases_asistidas = 0

    alumno_row = df[df["RUT"] == rut].iloc[0]
    monto_pagado = pagos[pagos["RUT"] == rut]["Monto Pagado"].sum()
    clases_plan = alumno_row["Clases por Semana"] * 4
    esperado = clases_plan * alumno_row["Valor Clase"]
    clases_plan = alumno_row["Clases por Semana"] * 4
    clases_plan = alumno_row["Clases por Semana"] * 4
    esperado = clases_plan * alumno_row["Valor Clase"]
    deuda = esperado - monto_pagado

    st.markdown(f"**Alumno:** {alumno_estado}")
    st.markdown(f"**Clases Asistidas:** {clases_asistidas}")
    st.markdown(f"**Plan Mensual:** {clases_plan} clases")
    st.markdown(f"**Valor Mensual:** ${esperado:,.0f}")
    st.markdown(f"**Monto Esperado:** ${esperado:,.0f}")
    st.markdown(f"**Monto Pagado:** ${monto_pagado:,.0f}")
    st.markdown(f"**Deuda:** ${deuda:,.0f}")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Estado de Pago - {alumno_estado} ({mes})", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, f"Clases Asistidas: {clases_asistidas}", ln=True)
    pdf.cell(0, 10, f"Plan Mensual: {clases_plan} clases", ln=True)
    pdf.cell(0, 10, f"Valor por Clase: ${alumno_row.get('Valor Clase', 0):,.0f}", ln=True)
    pdf.cell(0, 10, f"Monto Esperado: ${esperado:,.0f}", ln=True)
    pdf.cell(0, 10, f"Monto Pagado: ${monto_pagado:,.0f}", ln=True)
    pdf.cell(0, 10, f"Deuda: ${deuda:,.0f}", ln=True)

    try:
        os.makedirs("estados_pago", exist_ok=True)
        nombre_pdf = os.path.join("estados_pago", f"Estado_Pago_{alumno_estado.replace(' ', '_')}_{mes}.pdf")
        pdf.output(nombre_pdf)
        with open(nombre_pdf, "rb") as f:
            st.download_button("📥 Descargar PDF", f, file_name=f"Estado_Pago_{alumno_estado}_{mes}.pdf")
    except Exception as e:
        st.error(f"No se pudo generar el PDF: {e}")
        st.stop()


# --- RESUMEN MENSUAL PDF ---

elif menu == "Resumen Mensual PDF":
    st.subheader("📑 Generar y Ver Resumen PDF")
    mes = datetime.now().strftime("%m-%Y")

    try:
        pagos = pd.read_excel(archivo_excel, sheet_name=f"Pagos_{mes}")
    except:
        pagos = pd.DataFrame(columns=["RUT", "Monto Pagado"])

    asistencias = []
    with pd.ExcelFile(archivo_excel) as xls:
        for hoja in xls.sheet_names:
            if hoja.startswith("Asistencia_") and mes in hoja:
                asistencias.append(pd.read_excel(xls, sheet_name=hoja))

    if asistencias:
        df_asis = pd.concat(asistencias)
        asistidas = df_asis[df_asis["Estado"] == "Asistente"].groupby("RUT").size().reset_index(name="Clases Asistidas")
    else:
        asistidas = pd.DataFrame(columns=["RUT", "Clases Asistidas"])

    df_filtrado = filtrar(df.copy())
    resumen = df_filtrado.merge(asistidas, on="RUT", how="left").merge(pagos, on="RUT", how="left")
    resumen["Clases Plan"] = resumen["Clases por Semana"] * 4
    resumen["Esperado"] = resumen["Clases Plan"] * resumen["Valor Clase"]
    resumen["Clases Asistidas"] = resumen["Clases Asistidas"].fillna(0).astype(int)
    resumen["Monto Pagado"] = resumen["Monto Pagado"].fillna(0)
    resumen["Clases Plan"] = resumen.get("Clases por Semana", 1).fillna(1).astype(int) * 4
    
    resumen["Deuda"] = resumen["Esperado"] - resumen["Monto Pagado"]

    st.dataframe(resumen[["Nombre", "Curso", "Sección", "Clases Asistidas", "Valor Clase", "Monto Pagado", "Esperado", "Deuda"]])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Resumen Mensual Ajedrez - {mes}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    for col in ["Nombre", "Curso", "Sección", "Clases Asistidas", "Esperado", "Monto Pagado", "Deuda"]:
        pdf.cell(30, 10, col[:12], 1)
    pdf.ln()
    pdf.set_font("Arial", size=9)
    for _, row in resumen.iterrows():
        pdf.cell(30, 10, str(row["Nombre"])[:12], 1)
        pdf.cell(30, 10, str(row["Curso"]), 1)
        pdf.cell(30, 10, str(row["Sección"]), 1)
        pdf.cell(30, 10, str(row["Clases Asistidas"]), 1)
        pdf.cell(30, 10, f"${row['Esperado']:,.0f}", 1)
        pdf.cell(30, 10, f"${row['Monto Pagado']:,.0f}", 1)
        deuda_txt = f"${row['Deuda']:,.0f}" if row['Deuda'] > 0 else "-"
        pdf.cell(30, 10, deuda_txt, 1)
        pdf.ln()

    total_recaudado = resumen["Monto Pagado"].sum()
    total_adeudado = resumen["Deuda"].sum()
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total Recaudado: ${total_recaudado:,.0f}", ln=True)
    pdf.cell(0, 10, f"Total Adeudado: ${total_adeudado:,.0f}", ln=True)

    nombre_archivo = f"Resumen_Mensual_Ajedrez_{mes}.pdf"
    pdf.output(nombre_archivo)

    with open(nombre_archivo, "rb") as f:
        st.download_button("📥 Descargar Resumen PDF", f, file_name=nombre_archivo)
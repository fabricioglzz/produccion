import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================
# 1. Configuración inicial
# ==========================

st.set_page_config(
    page_title="Dashboard Límites FVT",
    layout="wide"
)

st.title("Dashboard de límites por FVT, variante (CD/CW) y pieza (Variable)")

st.write(
    "Este dashboard muestra los **límites inferior (LIC) y superior (LSC)** "
    "para cada pieza (Variable), por modelo FVT y variante (CD/CW). "
    "Se utilizan métricas como el rango (LSC − LIC) y el centro del intervalo."
)

# ==========================
# 2. Cargar datos
# ==========================

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    return df

# Cambia el nombre del archivo si es necesario
FILE_PATH = "LIMITESANGLE.csv"

df = load_data(FILE_PATH)

# Ajusta estos nombres si tus columnas se llaman distinto
col_base = "Base"
col_var  = "Variable"
col_lic  = "LIC"
col_lsc  = "LSC"

st.write("Columnas detectadas:", list(df.columns))

# ==========================
# 3. Columnas derivadas
# ==========================

df["Rango"]  = df[col_lsc] - df[col_lic]
df["Centro"] = (df[col_lsc] + df[col_lic]) / 2

# ==========================
# 4. Filtros en la barra lateral
# ==========================

st.sidebar.header("Filtros")

bases_unicas = sorted(df[col_base].unique())
vars_unicas  = sorted(df[col_var].unique())

bases_sel = st.sidebar.multiselect(
    "Selecciona FVT/Base",
    options=bases_unicas,
    default=bases_unicas
)

vars_sel = st.sidebar.multiselect(
    "Selecciona Variables (piezas)",
    options=vars_unicas,
    default=vars_unicas
)

df_filt = df[
    df[col_base].isin(bases_sel) &
    df[col_var].isin(vars_sel)
].copy()

if df_filt.empty:
    st.warning("No hay datos para esta combinación de filtros. Ajusta la Base o Variable.")
    st.stop()

# ==========================
# ==========================
# 5. KPIs generales
# ==========================

# Seguimos calculando Rango porque lo usas en el resto del dashboard
df_filt["Rango"] = df_filt[col_lsc] - df_filt[col_lic]

# Límites inferiores (LIC)
lic_max_row = df_filt.loc[df_filt[col_lic].idxmax()]
lic_min_row = df_filt.loc[df_filt[col_lic].idxmin()]

# Límites superiores (LSC)
lsc_max_row = df_filt.loc[df_filt[col_lsc].idxmax()]
lsc_min_row = df_filt.loc[df_filt[col_lsc].idxmin()]

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "LIC máximo",
    f"{lic_max_row[col_lic]:.2f}",
    f"{lic_max_row[col_base]} – {lic_max_row[col_var]}"
)

c2.metric(
    "LIC mínimo",
    f"{lic_min_row[col_lic]:.2f}",
    f"{lic_min_row[col_base]} – {lic_min_row[col_var]}"
)

c3.metric(
    "LSC máximo",
    f"{lsc_max_row[col_lsc]:.2f}",
    f"{lsc_max_row[col_base]} – {lsc_max_row[col_var]}"
)

c4.metric(
    "LSC mínimo",
    f"{lsc_min_row[col_lsc]:.2f}",
    f"{lsc_min_row[col_base]} – {lsc_min_row[col_var]}"
)

st.markdown("---")

# ==========================
# 6. Tabs para organizar las gráficas
#    Orden nuevo:
#    1) LIC vs LSC por Variable (1 Base)
#    2) Detalle promedio por Variable
#    3) Heatmap
# ==========================

tab1, tab2, tab3 = st.tabs([
    "LIC vs LSC por Variable (1 Base)",
    "Detalle por Variable (promedios)",
    "Heatmap FVT × Variable (Rango)"
])

# ==========================
# Tab 1: LIC vs LSC por Variable para una sola Base
# ==========================

with tab1:
    st.subheader("Límites LIC y LSC por Variable para una base específica")

    if len(bases_sel) == 1:
        base_seleccionada = bases_sel[0]
        st.write(f"Base seleccionada: **{base_seleccionada}**")

        df_base = df_filt[df_filt[col_base] == base_seleccionada].copy()

        if df_base.empty:
            st.warning("No hay datos para esta base con las variables seleccionadas.")
        else:
            # Reorganizar en formato largo para tener LIC y LSC como categorías
            df_melt = df_base.melt(
                id_vars=[col_var],
                value_vars=[col_lic, col_lsc],
                var_name="Tipo_Límite",
                value_name="Valor"
            )

            fig_bar_limits = px.bar(
                df_melt,
                x=col_var,
                y="Valor",
                color="Tipo_Límite",
                barmode="group",
                title=f"Límites inferior (LIC) y superior (LSC) por Variable – {base_seleccionada}",
                color_discrete_map={
                    col_lic: "#4c78a8",   # azul para LIC
                    col_lsc: "#1f77b4"    # azul más intenso para LSC
                },
                text_auto=True
            )

            fig_bar_limits.update_layout(
                xaxis_title="Variable (pieza)",
                yaxis_title="Valor del límite",
                legend_title="Tipo de límite"
            )

            st.plotly_chart(fig_bar_limits, use_container_width=True)
    else:
        st.info(
            "Para ver esta gráfica, selecciona **exactamente una** Base/FVT en la barra lateral."
        )

# ==========================
# Tab 2: Detalle LSC vs LIC por Variable (promedios) + barras solo LIC y solo LSC
# ==========================

with tab2:
    st.subheader("Comparación promedio LSC vs LIC por Variable")

    df_vars = (
        df_filt.groupby(col_var)[[col_lsc, col_lic]]
        .mean()
        .reset_index()
        .sort_values(col_var)
    )

    # --- Gráfica de líneas LSC vs LIC promedio ---
    fig_detalle = go.Figure()
    fig_detalle.add_trace(go.Scatter(
        x=df_vars[col_var],
        y=df_vars[col_lsc],
        mode="lines+markers",
        name="LSC (promedio)",
        line=dict(color="#1f77b4")
    ))
    fig_detalle.add_trace(go.Scatter(
        x=df_vars[col_var],
        y=df_vars[col_lic],
        mode="lines+markers",
        name="LIC (promedio)",
        line=dict(color="#0d3b66")
    ))
    fig_detalle.update_layout(
        title="Límites promedio LSC vs LIC por Variable (todas las Bases filtradas)",
        xaxis_title="Variable (pieza)",
        yaxis_title="Valor",
        legend_title="Límite"
    )

    st.plotly_chart(fig_detalle, use_container_width=True)

    st.markdown("### Barras individuales de límites promedio por Variable")

    # --- Gráfica de barras solo LIC promedio ---
    fig_lic_bar = px.bar(
        df_vars,
        x=col_var,
        y=col_lic,
        title="Límite inferior (LIC) promedio por Variable",
        text_auto=True,
        color_discrete_sequence=["#4c78a8"]
    )
    fig_lic_bar.update_layout(
        xaxis_title="Variable (pieza)",
        yaxis_title="LIC promedio"
    )

    # --- Gráfica de barras solo LSC promedio ---
    fig_lsc_bar = px.bar(
        df_vars,
        x=col_var,
        y=col_lsc,
        title="Límite superior (LSC) promedio por Variable",
        text_auto=True,
        color_discrete_sequence=["#1f77b4"]
    )
    fig_lsc_bar.update_layout(
        xaxis_title="Variable (pieza)",
        yaxis_title="LSC promedio"
    )

    c_bar1, c_bar2 = st.columns(2)
    with c_bar1:
        st.plotly_chart(fig_lic_bar, use_container_width=True)
    with c_bar2:
        st.plotly_chart(fig_lsc_bar, use_container_width=True)

    st.markdown("### Datos filtrados")
    st.dataframe(df_filt[[col_base, col_var, col_lic, col_lsc, "Rango", "Centro"]])

# ==========================
# Tab 3: Heatmap FVT × Variable del rango
# ==========================

with tab3:
    st.subheader("Mapa de calor del rango (LSC − LIC) por FVT/Base y Variable")

    df_heat = df_filt.pivot_table(
        index=col_base,
        columns=col_var,
        values="Rango",
        aggfunc="mean"
    )

    fig_heat = px.imshow(
        df_heat,
        color_continuous_scale="Blues",
        aspect="auto",
        origin="lower",
        labels=dict(color="Rango"),
        title="Heatmap del rango (LSC − LIC) por FVT/Base y Variable"
    )

    st.plotly_chart(fig_heat, use_container_width=True)

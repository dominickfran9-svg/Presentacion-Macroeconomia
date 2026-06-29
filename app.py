import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Dashboard Macroeconomía - DANE", page_icon="📊", layout="wide")

DATA_DIR = Path(__file__).resolve().parent / "data"


def normalize_header(value):
    return str(value).strip()


def get_theme_colors(theme_mode: str):
    if str(theme_mode).lower() == "claro":
        return {
            "background": "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 45%, #cbd5e1 100%)",
            "page_text": "#0f172a",
            "muted_text": "#475569",
            "card_bg": "rgba(255,255,255,0.72)",
            "border": "rgba(15,23,42,0.14)",
            "button_bg": "rgba(255,255,255,0.9)",
        }
    return {
        "background": "linear-gradient(180deg, #020617 0%, #0b1f3a 45%, #07162d 100%)",
        "page_text": "#f8fafc",
        "muted_text": "#cbd5e1",
        "card_bg": "rgba(255,255,255,0.08)",
        "border": "rgba(255,255,255,0.16)",
        "button_bg": "rgba(255,255,255,0.12)",
    }


def apply_theme_css(theme_mode: str):
    theme = get_theme_colors(theme_mode)
    st.markdown(
        f"""
        <style>
            .stApp {{
                background: {theme['background']} !important;
                color: {theme['page_text']} !important;
            }}
            .stApp * {{
                color: {theme['page_text']} !important;
            }}
            .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stText, .stTextInput>div>div>input,
            .stButton>button, .stCheckbox, .stRadio, .stRadio>div, .stSlider, .stSelectbox, .stTextArea {{
                color: {theme['page_text']} !important;
            }}
            .stButton>button, .stCheckbox label, .stRadio label {{
                background: {theme['button_bg']} !important;
                border: 1px solid {theme['border']} !important;
                backdrop-filter: blur(12px);
                box-shadow: 0 18px 48px rgba(0,0,0,0.12);
            }}
            .stTabs [role="tab"] {{
                background: rgba(255,255,255,0.10) !important;
                border: 1px solid {theme['border']} !important;
                border-radius: 999px !important;
                padding: 0.6rem 1rem !important;
                color: {theme['page_text']} !important;
                backdrop-filter: blur(14px);
            }}
            .stDataFrame td, .stDataFrame th, .stTable td, .stTable th {{
                color: {theme['page_text']} !important;
            }}
            .section-title {{
                opacity: 0;
                animation: fadeInSection 0.9s ease forwards;
            }}
            @keyframes fadeInSection {{
                from {{ opacity: 0; transform: translateY(18px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .glass-card {{
                background: {theme['card_bg']} !important;
                border: 1px solid {theme['border']} !important;
                box-shadow: 0 24px 60px rgba(0,0,0,0.16);
                backdrop-filter: blur(18px);
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_plotly(fig: go.Figure, theme_mode: str):
    theme = get_theme_colors(theme_mode)
    fig.update_layout(
        template="plotly_dark" if str(theme_mode).lower() != "claro" else "plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=theme["page_text"],
        legend_font_color=theme["page_text"],
        title_font_color=theme["page_text"],
        xaxis=dict(color=theme["page_text"], gridcolor="rgba(255,255,255,0.12)"),
        yaxis=dict(color=theme["page_text"], gridcolor="rgba(255,255,255,0.12)"),
    )
    return fig


@st.cache_data
def read_excel_sheet(file_name: str, sheet_name, header: int):
    path = DATA_DIR / file_name
    if not path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=header)
        df.columns = [normalize_header(col) for col in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


def parse_year_columns(df: pd.DataFrame):
    years = []
    for col in df.columns:
        col_text = str(col).strip()
        if re.match(r"^\d{4}(?:p|pr)?$", col_text, flags=re.IGNORECASE):
            years.append(col_text)
    def sort_key(value: str):
        year = int(re.search(r"\d{4}", str(value)).group())
        suffix = 1 if str(value).lower().endswith("pr") or str(value).lower().endswith("p") else 0
        return year, suffix
    return sorted(set(years), key=sort_key)


def clean_annual_sheet(df: pd.DataFrame, id_columns: list[str]):
    if df.empty:
        return df

    df = df.copy()
    df.columns = [normalize_header(col) for col in df.columns]
    source_col = next((col for col in id_columns if col in df.columns), None)

    if source_col:
        df["Concepto"] = df[source_col].astype(str).fillna("")
    else:
        df["Concepto"] = df.iloc[:, 0].astype(str).fillna("")

    df["Concepto"] = df["Concepto"].str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["Concepto"].astype(bool)].copy()

    year_columns = parse_year_columns(df)
    if not year_columns:
        return df[["Concepto"]].copy()

    df = df[["Concepto"] + year_columns].copy()
    df[year_columns] = df[year_columns].apply(pd.to_numeric, errors="coerce")
    return df


def load_main_pib():
    df = read_excel_sheet("PIB_Total y por habitante a precios corrientes.xlsx", sheet_name=0, header=6)
    if df.empty:
        return df

    rename_map = {
        "Año(aaaa)": "Año",
        "Año (aaaa)": "Año",
        "Año": "Año",
        "Total en miles de millones de pesos colombianos": "PIB_Total_COP",
        "Total variación porcentual anual %": "Crecimiento_Anual_%",
        "Por habitante en pesos colombianos": "PIB_Per_Capita_COP",
    }
    df = df.rename(columns=rename_map)
    df.columns = [normalize_header(col) for col in df.columns]

    if "Año" not in df.columns:
        return pd.DataFrame()

    df = df.dropna(subset=["Año"]).copy()
    df["Año"] = pd.to_numeric(df["Año"], errors="coerce")
    df = df.dropna(subset=["Año"]).copy()
    df["Año"] = df["Año"].astype(int)
    df = df.sort_values(by="Año").reset_index(drop=True)
    df["Año_str"] = df["Año"].astype(str)

    if "PIB_Total_COP" in df.columns:
        df["PIB_Total_COP"] = pd.to_numeric(df["PIB_Total_COP"], errors="coerce")
    if "Crecimiento_Anual_%" in df.columns:
        df["Crecimiento_Anual_%"] = pd.to_numeric(df["Crecimiento_Anual_%"], errors="coerce")
    if "PIB_Per_Capita_COP" in df.columns:
        df["PIB_Per_Capita_COP"] = pd.to_numeric(df["PIB_Per_Capita_COP"], errors="coerce")
    return df


def load_agregados():
    df_sector = clean_annual_sheet(
        read_excel_sheet("Agregados Macroeconomicos-2024pr.xlsx", sheet_name="Cuadro 1", header=9),
        ["Concepto"],
    )
    df_consumo = clean_annual_sheet(
        read_excel_sheet("Agregados Macroeconomicos-2024pr.xlsx", sheet_name="Cuadro 3", header=9),
        ["Concepto"],
    )
    df_consumo_alt = clean_annual_sheet(
        read_excel_sheet("Agregados Macroeconomicos-2024pr.xlsx", sheet_name="Cuadro 4", header=9),
        ["Concepto"],
    )
    df_income = clean_annual_sheet(
        read_excel_sheet("Agregados Macroeconomicos-2024pr.xlsx", sheet_name="Cuadro 5", header=9),
        ["Concepto"],
    )
    return df_sector, df_consumo, df_consumo_alt, df_income


def load_quarterly():
    df = read_excel_sheet("PIB DANE anex-GastoConstantes.xlsx", sheet_name="Cuadro 1", header=10)
    if df.empty:
        return df

    df = df.copy()
    df.columns = [normalize_header(col) for col in df.columns]
    if len(df.columns) >= 2:
        df["Concepto"] = (
            df.iloc[:, 0].astype(str).fillna("") + " " + df.iloc[:, 1].astype(str).fillna("")
        ).str.replace(r"\s+", " ", regex=True).str.strip()
    else:
        df["Concepto"] = df.iloc[:, 0].astype(str).fillna("")

    df = df[df["Concepto"].astype(bool)].copy()
    quarter_cols = [col for col in df.columns if isinstance(col, str) and re.fullmatch(r"(?:I|II|III|IV)(?:\.[0-9]+)?", col)]
    if not quarter_cols:
        return df[["Concepto"]].copy()

    df = df[["Concepto"] + quarter_cols].copy()
    df[quarter_cols] = df[quarter_cols].apply(pd.to_numeric, errors="coerce")
    return df


@st.cache_data
def load_trade_data():
    df_exports = read_excel_sheet("PIB DANE anex-GastoConstantes.xlsx", sheet_name="Cuadro 7", header=10)
    df_imports = read_excel_sheet("PIB DANE anex-GastoConstantes.xlsx", sheet_name="Cuadro 8", header=10)
    return df_exports, df_imports


@st.cache_data
def load_investment_data():
    return read_excel_sheet("PIB DANE anex-GastoConstantes.xlsx", sheet_name="Cuadro 2", header=10)


@st.cache_data
def load_institutional_data():
    df = read_excel_sheet("Agregados Macroeconomicos-2024pr.xlsx", sheet_name="Cuadro 6 ", header=9)
    if df.empty:
        return df

    df = df.copy()
    df.columns = [normalize_header(col) for col in df.columns]
    if "Unnamed: 1" in df.columns:
        df["Concepto"] = df["Unnamed: 1"].astype(str).fillna("")
    else:
        df["Concepto"] = df.iloc[:, 1].astype(str).fillna("")

    df["Concepto"] = df["Concepto"].str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["Concepto"].astype(bool)].copy()
    numeric_cols = [col for col in df.columns if col not in ["Unnamed: 0", "Unnamed: 1", "Concepto"]]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return df


def parse_quarter_columns(df: pd.DataFrame):
    return [col for col in df.columns if isinstance(col, str) and re.fullmatch(r"(?:I|II|III|IV)(?:\.[0-9]+)?", col)]


def prepare_quarterly_melt(df: pd.DataFrame, df_pib: pd.DataFrame | None = None):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    if "Concepto" not in df.columns:
        if "Unnamed: 0" in df.columns and "Unnamed: 1" in df.columns:
            df["Concepto"] = (
                df["Unnamed: 0"].astype(str).fillna("") + " " + df["Unnamed: 1"].astype(str).fillna("")
            ).str.replace(r"\s+", " ", regex=True).str.strip()
        else:
            df["Concepto"] = df.iloc[:, 0].astype(str).fillna("").str.strip()

    df["Concepto"] = df["Concepto"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df["Concepto"].astype(bool)].copy()

    quarter_cols = parse_quarter_columns(df)
    if not quarter_cols:
        return pd.DataFrame()

    def group_year_index(value: str):
        if "." in value:
            return int(value.split(".")[-1])
        return 0

    year_groups = sorted({group_year_index(str(col)) for col in quarter_cols})
    if df_pib is not None and not df_pib.empty:
        base_year = int(df_pib["Año"].max()) - len(year_groups) + 1
        if base_year < 1900:
            base_year = 2005
    else:
        base_year = 2005

    df_melt = df.melt(id_vars=["Concepto"], value_vars=quarter_cols, var_name="Trimestre", value_name="Valor")
    df_melt = df_melt.dropna(subset=["Valor"]).copy()
    df_melt["Valor"] = pd.to_numeric(df_melt["Valor"], errors="coerce")
    df_melt = df_melt.dropna(subset=["Valor"]).copy()
    df_melt["Trimestre"] = df_melt["Trimestre"].astype(str).str.strip()
    df_melt["Año"] = df_melt["Trimestre"].apply(lambda val: str(base_year + group_year_index(val)))
    df_melt["Periodo"] = df_melt["Año"] + " " + df_melt["Trimestre"].apply(lambda val: val.split(".")[0])
    return df_melt


def build_yearly_table(df: pd.DataFrame, latest_year: str | None, top_n: int = 6):
    if df.empty or latest_year is None or latest_year not in df.columns:
        return df.head(top_n)
    return df.sort_values(by=latest_year, ascending=False).head(top_n)


def render_intro():
    st.markdown(
        """
        <style>
            .intro-card {
                position: relative;
                overflow: hidden;
                padding: 3rem 2rem;
                border-radius: 32px;
                background: radial-gradient(circle at top left, rgba(59,130,246,0.24), transparent 28%),
                            radial-gradient(circle at bottom right, rgba(16,185,129,0.18), transparent 24%),
                            linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
                color: #f8fafc;
                box-shadow: 0 32px 80px rgba(15, 23, 42, 0.24);
                margin-bottom: 2rem;
                animation: fadeInUp 1.2s ease backwards;
            }
            .intro-card h1 {
                margin: 0 0 0.5rem 0;
                font-size: 3rem;
                letter-spacing: 0.08em;
                line-height: 1.05;
            }
            .intro-card p {
                margin: 0.4rem 0 0 0;
                color: rgba(241, 245, 249, 0.92);
                font-size: 1.05rem;
            }
            .hero-names {
                margin-top: 1.25rem;
                line-height: 1.7;
                font-size: 1.02rem;
                color: rgba(241, 245, 249, 0.92);
            }
            .hero-tag {
                display: inline-flex;
                padding: 0.5rem 1rem;
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 999px;
                font-size: 0.95rem;
                margin-top: 0.75rem;
                letter-spacing: 0.08em;
                animation: pulseGlow 3.5s ease-in-out infinite;
            }
            .hero-dots {
                position: absolute;
                inset: 0;
                pointer-events: none;
                background-image: radial-gradient(circle at 20% 20%, rgba(255,255,255,0.14), transparent 19%),
                                  radial-gradient(circle at 80% 10%, rgba(16,185,129,0.18), transparent 16%),
                                  radial-gradient(circle at 50% 80%, rgba(59,130,246,0.16), transparent 22%);
                opacity: 0.86;
            }
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(40px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes pulseGlow {
                0%, 100% { transform: scale(1); opacity: 0.85; }
                50% { transform: scale(1.04); opacity: 1; }
            }
            .stApp {
                background: linear-gradient(180deg, #eff6ff 0%, #f8fafc 53%, #e2e8f0 100%) !important;
                color: #0f172a !important;
            }
            .stMarkdown p, .stTextInput>div>div>input, .stButton>button {
                color: #0f172a !important;
            }
            .stDataFrame td, .stDataFrame th, .stTable td, .stTable th {
                color: #0f172a !important;
            }
            .stMetricValue {
                color: #111827 !important;
            }
            .stMetricLabel {
                color: #334155 !important;
            }
            .stButton>button {
                background: linear-gradient(135deg, #2563eb, #14b8a6) !important;
                color: #ffffff !important;
            }
            .stTabs [role="tab"] {
                color: #0f172a !important;
            }
        </style>
        <div class="intro-card">
            <div class="hero-dots"></div>
            <div style="position: relative; z-index: 1;">
                <div class="hero-tag">Presentación Interactiva</div>
                <h1>Macroeconomía</h1>
                <p>Una experiencia visual y analítica con todos los datos de los tres Excel entregados.</p>
                <div class="hero-names">
                    <strong>Integrantes:</strong><br>
                    Mariana Vera Gonzales<br>
                    Maria Jose Vargas<br>
                    Dominick Franchesco Vargas Parra
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_intro()

st.title("📊 Dashboard Macroeconómico de Colombia")
st.markdown("Análisis interactivo de PIB, consumo, sectores e inversión con datos oficiales del DANE.")
st.markdown("---")


df_pib = load_main_pib()
df_sector, df_consumo, df_consumo_alt, df_income = load_agregados()
df_quarterly = load_quarterly()
df_exports, df_imports = load_trade_data()
df_investment = load_investment_data()
df_institutional = load_institutional_data()


with st.sidebar:
    st.header("Configuración")
    if not df_pib.empty:
        ano_min = int(df_pib["Año"].min())
        ano_max = int(df_pib["Año"].max())
        selected_year = st.slider("Rango de años", ano_min, ano_max, (max(ano_min, ano_max - 10), ano_max))
        selected_years = list(range(selected_year[0], selected_year[1] + 1))
    else:
        selected_years = []

    theme_mode = "Oscuro"
    show_raw = st.checkbox("Mostrar tablas de datos", value=False)
    st.markdown("---")
    st.markdown("*Fuente de datos: DANE - Archivos Excel en la carpeta `data`.*")

apply_theme_css(theme_mode)


st.subheader("Indicadores Clave")
if df_pib.empty:
    st.error("No se pudo cargar el archivo principal de PIB. Verifica que el archivo exista en `venv/data`.")
else:
    latest = df_pib.iloc[-1]
    growth_label = f"{latest['Crecimiento_Anual_%']:.2f}%" if pd.notna(latest.get("Crecimiento_Anual_%")) else "N/A"
    avg_growth = df_pib["Crecimiento_Anual_%"].tail(5).mean() if "Crecimiento_Anual_%" in df_pib.columns else None
    avg_growth_label = f"{avg_growth:.2f}%" if pd.notna(avg_growth) else "N/A"

    latest_consumption = None
    consumption_years = parse_year_columns(df_consumo) if not df_consumo.empty else []
    if consumption_years:
        latest_consumption = df_consumo[consumption_years[-1]].sum(skipna=True)
    latest_consumption_label = f"${latest_consumption:,.0f}" if latest_consumption is not None else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Año más reciente", latest["Año"])
    col2.metric("PIB total (COP)", f"${latest['PIB_Total_COP']:,.0f}" if pd.notna(latest.get("PIB_Total_COP")) else "N/A")
    col3.metric("PIB per cápita", f"${latest['PIB_Per_Capita_COP']:,.0f}" if pd.notna(latest.get("PIB_Per_Capita_COP")) else "N/A")
    col4.metric("Crecimiento anual", growth_label)

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Crecimiento 5 años", avg_growth_label)
    col6.metric("Consumo total último año", latest_consumption_label)
    col7.metric("Años disponibles", f"{int(df_pib['Año'].min())} - {int(df_pib['Año'].max())}")
    col8.metric("Tablas visibles", "Sí" if show_raw else "No")

    st.markdown("---")

    tabs = st.tabs([
        "📈 Evolución del PIB",
        "🏭 Sectores",
        "🛒 Consumo",
        "📅 PIB Trimestral",
        "💰 Ingresos e inversión",
        "🌍 Comercio exterior"
    ])

    with tabs[0]:
        st.subheader("Evolución histórica del PIB")
        df_pib_range = df_pib[df_pib["Año"].isin(selected_years)] if selected_years else df_pib
        series_to_plot = [col for col in ["PIB_Total_COP", "PIB_Per_Capita_COP"] if col in df_pib.columns]
        if series_to_plot:
            fig_pib = px.line(
                df_pib_range,
                x="Año",
                y=series_to_plot,
                markers=True,
                title="PIB Total y PIB Per Cápita",
                labels={"value": "COP", "variable": "Serie", "Año": "Año"}
            )
            fig_pib = style_plotly(fig_pib, theme_mode)
            fig_pib.update_layout(
                legend_title_text="Serie",
                hovermode="x unified"
            )
            st.plotly_chart(fig_pib, use_container_width=True)

        if "Crecimiento_Anual_%" in df_pib.columns:
            fig_growth = px.bar(
                df_pib_range,
                x="Año",
                y="Crecimiento_Anual_%",
                color="Crecimiento_Anual_%",
                color_continuous_scale=[(0, "#ef4444"), (0.5, "#f59e0b"), (1, "#22c55e")],
                title="Crecimiento anual del PIB (%)"
            )
            fig_growth = style_plotly(fig_growth, theme_mode)
            fig_growth.update_layout(
                xaxis_title="Año",
                yaxis_title="% Crecimiento"
            )
            st.plotly_chart(fig_growth, use_container_width=True)

            fig_indicator = go.Figure(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=float(latest["Crecimiento_Anual_%"] if pd.notna(latest.get("Crecimiento_Anual_%")) else 0),
                    delta={"reference": float(avg_growth) if avg_growth is not None and pd.notna(avg_growth) else 0},
                    gauge={
                        "axis": {"range": [-10, max(20, float(latest.get("Crecimiento_Anual_%", 0)) * 2)]},
                        "bar": {"color": "#2563eb"},
                        "steps": [
                            {"range": [-10, 0], "color": "#fecaca"},
                            {"range": [0, 5], "color": "#fde68a"},
                            {"range": [5, 20], "color": "#86efac"}
                        ]
                    },
                    title={"text": "Crecimiento anual reciente"}
                )
            )
            fig_indicator = style_plotly(fig_indicator, theme_mode)
            st.plotly_chart(fig_indicator, use_container_width=True)

    with tabs[1]:
        st.subheader("Desglose sectorial del PIB")
        if df_sector.empty:
            st.warning("No hay datos sectoriales disponibles en Agregados Macroeconómicos.")
        else:
            latest_years = parse_year_columns(df_sector)
            if latest_years:
                target_year = latest_years[-1]
                df_top_sector = build_yearly_table(df_sector, target_year, top_n=8)
                fig_sector = px.bar(
                    df_top_sector,
                    x=target_year,
                    y="Concepto",
                    orientation="h",
                    color=target_year,
                    color_continuous_scale="teal",
                    title=f"Top 8 sectores de PIB en {target_year}",
                    labels={target_year: "Valor", "Concepto": "Sector"}
                )
                fig_sector.update_layout(
                    plot_bgcolor="rgba(255,255,255,0)",
                    paper_bgcolor="rgba(255,255,255,0)"
                )
                st.plotly_chart(fig_sector, use_container_width=True)

                sunburst_fig = px.sunburst(
                    df_top_sector,
                    path=["Concepto"],
                    values=target_year,
                    title=f"Composición sectorial del PIB en {target_year}",
                    color=target_year,
                    color_continuous_scale="Agsunset"
                )
                sunburst_fig.update_traces(textinfo="label+percent entry")
                st.plotly_chart(sunburst_fig, use_container_width=True)
            else:
                st.warning("No se encontraron columnas de año válidas en el desglose sectorial.")

    with tabs[2]:
        st.subheader("Consumo por categoría")
        if df_consumo.empty:
            st.warning("No hay datos de consumo disponibles en Agregados Macroeconómicos.")
        else:
            years = parse_year_columns(df_consumo)
            if years:
                df_top_consumo = build_yearly_table(df_consumo, years[-1], top_n=6)
                df_consumo_melt = df_top_consumo.melt(
                    id_vars=["Concepto"],
                    value_vars=years,
                    var_name="Año",
                    value_name="Valor"
                ).dropna(subset=["Valor"])
                fig_consumo = px.area(
                    df_consumo_melt,
                    x="Año",
                    y="Valor",
                    color="Concepto",
                    title="Consumo de los hogares por finalidad (Top 6)",
                    line_shape="spline"
                )
                fig_consumo.update_layout(
                    plot_bgcolor="rgba(255,255,255,0)",
                    paper_bgcolor="rgba(255,255,255,0)"
                )
                st.plotly_chart(fig_consumo, use_container_width=True)

                if not df_consumo_alt.empty:
                    alt_years = parse_year_columns(df_consumo_alt)
                    if alt_years:
                        df_top_alt = build_yearly_table(df_consumo_alt, alt_years[-1], top_n=5)
                        df_alt_melt = df_top_alt.melt(
                            id_vars=["Concepto"],
                            value_vars=alt_years,
                            var_name="Año",
                            value_name="Valor"
                        ).dropna(subset=["Valor"])
                        fig_alt = px.line(
                            df_alt_melt,
                            x="Año",
                            y="Valor",
                            color="Concepto",
                            markers=True,
                            title="Consumo por finalidad (alt)",
                            line_shape="spline"
                        )
                        fig_alt.update_layout(
                            plot_bgcolor="rgba(255,255,255,0)",
                            paper_bgcolor="rgba(255,255,255,0)"
                        )
                        st.plotly_chart(fig_alt, use_container_width=True)

                if show_raw:
                    st.markdown("**Datos de consumo (formato anual)**")
                    st.dataframe(df_top_consumo)
                    if not df_consumo_alt.empty:
                        st.dataframe(df_top_alt)
            else:
                st.warning("No se encontraron columnas de año válidas en los datos de consumo.")

    with tabs[3]:
        st.subheader("PIB trimestral y ritmo económico")
        if df_quarterly.empty:
            st.warning("No hay datos trimestrales disponibles en el archivo de PIB trimestral.")
        else:
            quarter_columns = [col for col in df_quarterly.columns if col != "Concepto"]
            if quarter_columns:
                recent_quarters = quarter_columns[:4]
                df_quarter = df_quarterly[["Concepto"] + recent_quarters].dropna(how="all", subset=recent_quarters)
                df_top_quarter = df_quarter.sort_values(by=recent_quarters[-1], ascending=False).head(6)
                df_quarter_melt = df_top_quarter.melt(
                    id_vars=["Concepto"],
                    value_vars=recent_quarters,
                    var_name="Trimestre",
                    value_name="Valor"
                )
                fig_quarter = px.bar(
                    df_quarter_melt,
                    x="Trimestre",
                    y="Valor",
                    color="Concepto",
                    barmode="group",
                    title="Perfil trimestral de los principales agregados"
                )
                fig_quarter.update_layout(
                    plot_bgcolor="rgba(255,255,255,0)",
                    paper_bgcolor="rgba(255,255,255,0)"
                )
                st.plotly_chart(fig_quarter, use_container_width=True)

                df_quarter_melt_full = prepare_quarterly_melt(df_quarterly, df_pib)
                if not df_quarter_melt_full.empty:
                    fig_quarter_line = px.line(
                        df_quarter_melt_full[df_quarter_melt_full["Concepto"].isin(df_top_quarter["Concepto"])],
                        x="Periodo",
                        y="Valor",
                        color="Concepto",
                        title="Evolución por trimestre (estructura anualizada)",
                        labels={"Valor": "Valor", "Periodo": "Periodo"}
                    )
                    fig_quarter_line.update_layout(
                        plot_bgcolor="rgba(255,255,255,0)",
                        paper_bgcolor="rgba(255,255,255,0)",
                        xaxis_title="Periodo"
                    )
                    st.plotly_chart(fig_quarter_line, use_container_width=True)

                if show_raw:
                    st.markdown("**Datos trimestrales (muestra)**")
                    st.dataframe(df_top_quarter)
            else:
                st.warning("No se encontraron columnas de trimestres válidas en los datos trimestrales.")

    with tabs[4]:
        st.subheader("Ingresos e inversión")
        if df_income.empty:
            st.warning("No hay datos de ingresos disponibles en Agregados Macroeconómicos.")
        else:
            income_years = parse_year_columns(df_income)
            if income_years:
                df_top_income = build_yearly_table(df_income, income_years[-1], top_n=8)
                fig_income = px.treemap(
                    df_top_income,
                    path=["Concepto"],
                    values=income_years[-1],
                    title=f"Componentes principales de ingreso nacional en {income_years[-1]}",
                    color=income_years[-1],
                    color_continuous_scale="Mint"
                )
                fig_income.update_traces(textinfo="label+value+percent entry")
                st.plotly_chart(fig_income, use_container_width=True)

                if not df_investment.empty:
                    df_invest_melt = prepare_quarterly_melt(df_investment, df_pib)
                    if not df_invest_melt.empty:
                        df_invest_year = df_invest_melt.groupby(["Concepto", "Año"], as_index=False)["Valor"].sum()
                        df_invest_top = df_invest_year[df_invest_year["Concepto"].str.contains(
                            "AN111|AN112|AN113|AN114|AN115|Vivienda|Maquinaria|Otros edificios",
                            case=False,
                            regex=True,
                            na=False,
                        )]
                        if not df_invest_top.empty:
                            fig_invest = px.area(
                                df_invest_top,
                                x="Año",
                                y="Valor",
                                color="Concepto",
                                title="Inversión bruta de capital por categoría",
                                labels={"Valor": "Valor", "Año": "Año"}
                            )
                            fig_invest.update_layout(
                                plot_bgcolor="rgba(255,255,255,0)",
                                paper_bgcolor="rgba(255,255,255,0)"
                            )
                            st.plotly_chart(fig_invest, use_container_width=True)

                if show_raw:
                    st.markdown("**Ingresos e inversión (datos completos)**")
                    st.dataframe(df_top_income)
                    st.dataframe(df_investment)
            else:
                st.warning("No se encontraron años válidos en los datos de ingresos.")

    with tabs[5]:
        st.subheader("Comercio exterior")
        if df_exports.empty or df_imports.empty:
            st.warning("No hay datos de comercio exterior disponibles en los archivos de DANE.")
        else:
            exports_melt = prepare_quarterly_melt(df_exports, df_pib)
            imports_melt = prepare_quarterly_melt(df_imports, df_pib)
            if not exports_melt.empty and not imports_melt.empty:
                exports_year = exports_melt.groupby(["Concepto", "Año"], as_index=False)["Valor"].sum()
                imports_year = imports_melt.groupby(["Concepto", "Año"], as_index=False)["Valor"].sum()
                exports_year["Valor"] = pd.to_numeric(exports_year["Valor"], errors="coerce")
                imports_year["Valor"] = pd.to_numeric(imports_year["Valor"], errors="coerce")
                exports_year = exports_year.dropna(subset=["Valor"]).copy()
                imports_year = imports_year.dropna(subset=["Valor"]).copy()
                latest_year = str(sorted(exports_year["Año"].unique())[-1]) if not exports_year.empty else None

                top_exports = exports_year[exports_year["Año"] == latest_year].nlargest(6, "Valor") if latest_year else pd.DataFrame()
                top_imports = imports_year[imports_year["Año"] == latest_year].nlargest(6, "Valor") if latest_year else pd.DataFrame()
                combined = pd.concat([
                    top_exports.assign(Tipo="Exportaciones"),
                    top_imports.assign(Tipo="Importaciones")
                ], ignore_index=True)

                if not combined.empty:
                    fig_trade = px.line(
                        combined,
                        x="Año",
                        y="Valor",
                        color="Concepto",
                        line_dash="Tipo",
                        markers=True,
                        title="Evolución de comercio exterior (principales partidas)",
                        labels={"Valor": "Valor", "Año": "Año", "Tipo": "Tipo"}
                    )
                    fig_trade = style_plotly(fig_trade, theme_mode)
                    st.plotly_chart(fig_trade, use_container_width=True)

                if latest_year and not combined.empty:
                    st.markdown(f"### Principales partidas en {latest_year}")
                    st.dataframe(combined.sort_values(by=["Tipo", "Valor"], ascending=[True, False]).reset_index(drop=True))
            else:
                st.warning("No se pudieron preparar los datos de comercio exterior.")

            if not df_institutional.empty:
                st.markdown("---")
                st.subheader("Sector institucional")
                inst_cols = [col for col in df_institutional.columns if col not in ["Unnamed: 0", "Unnamed: 1", "Concepto"]]
                if inst_cols:
                    best_col = inst_cols[-2] if len(inst_cols) > 1 else inst_cols[0]
                    df_inst_chart = df_institutional.sort_values(by=best_col, ascending=False).head(8)
                    fig_inst = px.bar(
                        df_inst_chart,
                        x=best_col,
                        y="Concepto",
                        orientation="h",
                        color=best_col,
                        title=f"Sector institucional - {best_col}",
                        labels={best_col: "Valor", "Concepto": "Elemento"}
                    )
                    fig_inst.update_layout(plot_bgcolor="rgba(255,255,255,0)", paper_bgcolor="rgba(255,255,255,0)")
                    st.plotly_chart(fig_inst, use_container_width=True)

                if show_raw:
                    st.markdown("**Datos sector institucional**")
                    st.dataframe(df_institutional)

    if show_raw:
        st.markdown("---")
        st.subheader("Tablas completas de datos cargados")
        st.write("### PIB anual")
        st.dataframe(df_pib)
        st.write("### Sectores del PIB")
        st.dataframe(df_sector)
        st.write("### Consumo por finalidad")
        st.dataframe(df_consumo)
        st.write("### Consumo alternativa")
        st.dataframe(df_consumo_alt)
        st.write("### Ingresos nacionales")
        st.dataframe(df_income)
        st.write("### Trimestrales")
        st.dataframe(df_quarterly)
        st.write("### Exportaciones")
        st.dataframe(df_exports)
        st.write("### Importaciones")
        st.dataframe(df_imports)
        st.write("### Inversión")
        st.dataframe(df_investment)
        st.write("### Sector institucional")
        st.dataframe(df_institutional)

st.markdown("---")
st.markdown("*Desarrollado para análisis macroeconómico con datos del DANE.*")

import json
import os
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

st.set_page_config(page_title="Car TCO Comparison", layout="wide")

SETTINGS_FILE = "settings.json"
SETTINGS_DEFAULTS = {
    "years": 7,
    "city_mi": 2500,
    "hwy_mi": 2500,
    "discount_pct": 5.0,
    "purchase_type": "Auto",
    "makes": [],
    "powertrains": [],
    "year_range": [2018, 2026],
    "max_price": None,  # filled after CSV loads
    "req_cpo": False,
    "req_hvac": False,
    "req_awd": False,
    "req_aeb": False,
    "req_acc": False,
    "min_iihs": 0,
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                saved = json.load(f)
            s = SETTINGS_DEFAULTS.copy()
            s.update(saved)
            return s
        except Exception:
            pass
    return SETTINGS_DEFAULTS.copy()


def save_settings(s: dict) -> None:
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)

MAKE_COLORS = {
    "Toyota": "#DC2626",
    "Subaru": "#2563EB",
    "Honda": "#059669",
    "Ford": "#7C3AED",
    "Mazda": "#EA580C",
    "Hyundai": "#0891B2",
    "Kia": "#D97706",
}
PT_COLORS = {"Gas": "#6366F1", "Hybrid": "#059669", "PHEV": "#F59E0B"}


@st.cache_data
def load_data():
    df = pd.read_csv("Car Comparison - Sheet1.csv")

    for col in [
        "MSRP_New_Est",
        "Used_Price_Est_25K_mi",
        "Resale_7yr",
        "Scheduled_Maint_7yr",
        "Unscheduled_Repair_7yr",
        "Insurance_Annual",
    ]:
        df[col] = (
            df[col].astype(str).str.replace(r"[$,]", "", regex=True).str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Maint_7yr"] = df["Scheduled_Maint_7yr"].fillna(0) + df[
        "Unscheduled_Repair_7yr"
    ].fillna(0)

    df["Label"] = (
        df["Year"].astype(str)
        + " "
        + df["Make"]
        + " "
        + df["Model"]
        + " "
        + df["Trim"]
    )

    def broad_pt(p):
        if p == "PHEV":
            return "PHEV"
        if p == "Hybrid":
            return "Hybrid"
        return "Gas"

    df["Powertrain_Cat"] = df["Powertrain"].apply(broad_pt)

    def iihs_rank(r):
        if pd.isna(r):
            return 0
        r = str(r)
        if "TSP+" in r:
            return 2
        if "TSP" in r:
            return 1
        return 0

    df["IIHS_Rank"] = df["IIHS_Rating"].apply(iihs_rank)
    df["Has_Physical_HVAC"] = df["Physical_HVAC_Controls"] == "Yes"
    df["Has_AEB"] = df["AEB_Standard"] == "Yes"
    df["Has_ACC"] = df["ACC_Standard"] == "Yes"
    df["Has_AWD"] = df["AWD_Standard"] == "Yes"

    return df


def get_purchase_price(df: pd.DataFrame, purchase_type: str) -> pd.Series:
    if purchase_type == "Auto":
        return df.apply(
            lambda r: r["Used_Price_Est_25K_mi"]
            if r["Year"] <= 2024
            else r["MSRP_New_Est"],
            axis=1,
        )
    return df["MSRP_New_Est"]


def compute_tco(
    df: pd.DataFrame,
    years: int,
    city_mi: float,
    hwy_mi: float,
    discount_pct: float,
    purchase_type: str,
) -> pd.DataFrame:
    r = discount_pct / 100.0
    df = df.copy()

    df["Purchase"] = get_purchase_price(df, purchase_type)

    df["Annual_Fuel"] = (
        city_mi * df["Fuel_cost_city_per_mile"]
        + hwy_mi * df["Fuel_cost_hwy_per_mile"]
    )
    df["Annual_Insurance"] = df["Insurance_Annual"]
    df["Annual_Maint"] = df["Maint_7yr"] / 7.0
    df["Annual_Cost"] = df["Annual_Fuel"] + df["Annual_Insurance"] + df["Annual_Maint"]

    pv_factor = (1 - (1 + r) ** (-years)) / r if r > 0 else float(years)

    # Derive implied annual resale rate from the 7-year CSV value
    ratio = (df["Resale_7yr"] / (df["Purchase"] * 0.88)).clip(lower=0.001, upper=0.999)
    df["Implied_Rate"] = ratio ** (1.0 / 7.0)
    df["Resale_N"] = df["Purchase"] * (df["Implied_Rate"] ** years) * 0.88
    df["PV_Resale"] = df["Resale_N"] / ((1 + r) ** years)

    df["PV_Fuel"] = df["Annual_Fuel"] * pv_factor
    df["PV_Insurance"] = df["Annual_Insurance"] * pv_factor
    df["PV_Maint"] = df["Annual_Maint"] * pv_factor
    df["TCO"] = df["Purchase"] + df["Annual_Cost"] * pv_factor - df["PV_Resale"]

    return df


def apply_filters(
    df: pd.DataFrame,
    makes: list,
    powertrains: list,
    year_range: tuple,
    max_price: int,
    req_cpo: bool,
    req_hvac: bool,
    req_awd: bool,
    req_aeb: bool,
    req_acc: bool,
    min_iihs: int,
    purchase_type: str,
) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if makes:
        mask &= df["Make"].isin(makes)
    if powertrains:
        mask &= df["Powertrain_Cat"].isin(powertrains)
    mask &= df["Year"].between(year_range[0], year_range[1])
    price_series = get_purchase_price(df, purchase_type)
    mask &= price_series <= max_price
    if req_cpo:
        mask &= df["CPO_Available"] == "Yes"
    if req_hvac:
        mask &= df["Has_Physical_HVAC"]
    if req_awd:
        mask &= df["Has_AWD"]
    if req_aeb:
        mask &= df["Has_AEB"]
    if req_acc:
        mask &= df["Has_ACC"]
    if min_iihs > 0:
        mask &= df["IIHS_Rank"] >= min_iihs
    return df[mask].copy()


# ── Load ──────────────────────────────────────────────────────────────────────

df_raw = load_data()
s = load_settings()

# Fill max_price default from CSV if not yet saved
max_msrp = int(df_raw["MSRP_New_Est"].max())
if s["max_price"] is None:
    s["max_price"] = max_msrp

# Validate multiselect defaults against current CSV values
all_makes = sorted(df_raw["Make"].unique())
s["makes"] = [m for m in s["makes"] if m in all_makes]
s["powertrains"] = [p for p in s["powertrains"] if p in ["Gas", "Hybrid", "PHEV"]]
s["year_range"] = [
    max(2018, min(2026, s["year_range"][0])),
    max(2018, min(2026, s["year_range"][1])),
]
s["max_price"] = max(15_000, min(max_msrp, s["max_price"]))

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Parameters")
    if st.button("🔄 Reload CSV"):
        load_data.clear()
        st.rerun()

    st.subheader("Ownership")
    years = st.slider("Years of ownership", 1, 15, s["years"])
    city_mi = st.number_input(
        "Annual city miles", min_value=0, max_value=50_000, value=s["city_mi"], step=500
    )
    hwy_mi = st.number_input(
        "Annual hwy miles", min_value=0, max_value=50_000, value=s["hwy_mi"], step=500
    )
    discount_pct = st.slider("Discount rate (%)", 0.0, 10.0, s["discount_pct"], 0.5)
    purchase_type = st.radio(
        "Purchase type",
        ["Auto", "New (MSRP)"],
        index=["Auto", "New (MSRP)"].index(s["purchase_type"]),
        help="Auto = used price for 2018–2024, MSRP for 2025–2026",
    )

    st.divider()
    st.subheader("Filters")

    makes = st.multiselect("Make", all_makes, default=s["makes"], placeholder="All makes")
    powertrains = st.multiselect(
        "Powertrain", ["Gas", "Hybrid", "PHEV"], default=s["powertrains"], placeholder="All types"
    )
    year_range = st.slider("Model year range", 2018, 2026, tuple(s["year_range"]))
    max_price = st.slider(
        "Max purchase price", 15_000, max_msrp, s["max_price"], step=1_000, format="$%d"
    )

    st.divider()
    st.subheader("Required Features")
    req_cpo = st.toggle("CPO available", value=s["req_cpo"])
    req_hvac = st.toggle("Physical HVAC controls only", value=s["req_hvac"])
    req_awd = st.toggle("AWD standard", value=s["req_awd"])
    req_aeb = st.toggle("AEB standard", value=s["req_aeb"])
    req_acc = st.toggle("ACC standard", value=s["req_acc"])
    iihs_labels = {0: "Any", 1: "TSP or better", 2: "TSP+ only"}
    min_iihs = st.selectbox(
        "Min IIHS rating", options=[0, 1, 2], index=s["min_iihs"],
        format_func=lambda x: iihs_labels[x]
    )

    # Persist current values after every interaction
    save_settings({
        "years": years,
        "city_mi": int(city_mi),
        "hwy_mi": int(hwy_mi),
        "discount_pct": discount_pct,
        "purchase_type": purchase_type,
        "makes": makes,
        "powertrains": powertrains,
        "year_range": list(year_range),
        "max_price": max_price,
        "req_cpo": req_cpo,
        "req_hvac": req_hvac,
        "req_awd": req_awd,
        "req_aeb": req_aeb,
        "req_acc": req_acc,
        "min_iihs": min_iihs,
    })

# ── Compute ───────────────────────────────────────────────────────────────────

df_filtered = apply_filters(
    df_raw,
    makes,
    powertrains,
    year_range,
    max_price,
    req_cpo,
    req_hvac,
    req_awd,
    req_aeb,
    req_acc,
    min_iihs,
    purchase_type,
)
df = compute_tco(df_filtered, years, city_mi, hwy_mi, discount_pct, purchase_type)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Car TCO Comparison")
st.caption(
    f"{len(df)} vehicles · {years}yr ownership · "
    f"{city_mi:,} city + {hwy_mi:,} hwy mi/yr · "
    f"{discount_pct}% discount rate"
)

if df.empty:
    st.warning("No vehicles match the current filters.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏆 Rankings", "📊 Cost Breakdown", "🔵 Scatter", "📈 Sensitivity", "📋 Data Table"]
)

# ── Tab 1: Rankings ───────────────────────────────────────────────────────────

with tab1:
    n_vehicles = len(df)
    if n_vehicles <= 1:
        top_n = n_vehicles
    else:
        top_n = st.slider(
            "Show top N vehicles by TCO",
            1,
            min(100, n_vehicles),
            min(30, n_vehicles),
            key="top_n",
        )
    df_top = df.nsmallest(top_n, "TCO").sort_values("TCO", ascending=True)

    fig1 = go.Figure()
    for make in df_top["Make"].unique():
        sub = df_top[df_top["Make"] == make]
        fig1.add_trace(
            go.Bar(
                x=sub["TCO"],
                y=sub["Label"],
                name=make,
                orientation="h",
                marker_color=MAKE_COLORS.get(make, "#888"),
                customdata=sub[
                    ["Purchase", "PV_Fuel", "PV_Insurance", "PV_Maint", "PV_Resale", "Powertrain"]
                ].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "TCO: $%{x:,.0f}<br>"
                    "─────────────<br>"
                    "Purchase: $%{customdata[0]:,.0f}<br>"
                    "Fuel (PV): $%{customdata[1]:,.0f}<br>"
                    "Insurance (PV): $%{customdata[2]:,.0f}<br>"
                    "Maintenance (PV): $%{customdata[3]:,.0f}<br>"
                    "Resale credit: −$%{customdata[4]:,.0f}<br>"
                    "Powertrain: %{customdata[5]}"
                    "<extra></extra>"
                ),
            )
        )

    fig1.update_layout(
        height=max(400, top_n * 22),
        barmode="overlay",
        xaxis_title="Total Cost of Ownership ($)",
        xaxis_tickformat="$,.0f",
        yaxis={"categoryorder": "total descending"},
        legend_title="Make",
        margin=dict(l=0, r=20, t=10, b=40),
    )
    st.plotly_chart(fig1, use_container_width=True)

# ── Tab 2: Cost Breakdown ─────────────────────────────────────────────────────

with tab2:
    df_sorted_tco = df.sort_values("TCO")
    default_sel = df_sorted_tco["Label"].head(10).tolist()
    selected = st.multiselect(
        "Select vehicles to compare (sorted by TCO)",
        df_sorted_tco["Label"].tolist(),
        default=default_sel,
        key="breakdown_sel",
    )

    if not selected:
        st.info("Select vehicles above to see cost breakdown.")
    else:
        sub2 = df[df["Label"].isin(selected)].sort_values("TCO")

        component_map = {
            "Purchase": ("Purchase", "#4B5563"),
            "Fuel (PV)": ("PV_Fuel", "#F59E0B"),
            "Insurance (PV)": ("PV_Insurance", "#6366F1"),
            "Maintenance (PV)": ("PV_Maint", "#EF4444"),
            "Resale Credit": (None, "#059669"),
        }

        fig2 = go.Figure()
        for label, (col, color) in component_map.items():
            if col is not None:
                y_vals = sub2[col]
            else:
                y_vals = -sub2["PV_Resale"]
            fig2.add_trace(
                go.Bar(
                    name=label,
                    x=sub2["Label"],
                    y=y_vals,
                    marker_color=color,
                    hovertemplate=f"<b>{label}</b>: $%{{y:,.0f}}<extra></extra>",
                )
            )

        fig2.update_layout(
            barmode="relative",
            height=520,
            yaxis_title="Cost ($)",
            yaxis_tickformat="$,.0f",
            legend_title="Component",
            xaxis_tickangle=-30,
            margin=dict(b=130),
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "Resale Credit is negative — it reduces TCO. "
            "Net bar height = Total Cost of Ownership."
        )

# ── Tab 3: Scatter ────────────────────────────────────────────────────────────

with tab3:
    color_by = st.radio(
        "Color by", ["Powertrain", "Make"], horizontal=True, key="scatter_color"
    )

    df_scatter = df.copy()
    df_scatter["Cargo"] = df_scatter["Max_Cargo_cuft"].fillna(
        df_scatter["Max_Cargo_cuft"].median()
    )

    if color_by == "Powertrain":
        color_col = "Powertrain_Cat"
        color_map = PT_COLORS
        color_label = "Powertrain"
    else:
        color_col = "Make"
        color_map = MAKE_COLORS
        color_label = "Make"

    fig3 = px.scatter(
        df_scatter,
        x="Purchase",
        y="TCO",
        color=color_col,
        size="Cargo",
        size_max=18,
        hover_name="Label",
        hover_data={
            "Purchase": True,
            "TCO": True,
            "Powertrain": True,
            "Max_Cargo_cuft": True,
            color_col: False,
            "Cargo": False,
        },
        color_discrete_map=color_map,
        labels={
            "Purchase": "Purchase Price ($)",
            "TCO": "TCO ($)",
            "Powertrain_Cat": "Powertrain",
            "Max_Cargo_cuft": "Max Cargo (cu ft)",
        },
    )
    fig3.update_layout(
        height=600,
        xaxis_tickformat="$,.0f",
        yaxis_tickformat="$,.0f",
        legend_title=color_label,
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Bubble size = max cargo space (cu ft). Hover for details.")

# ── Tab 4: Sensitivity ────────────────────────────────────────────────────────

with tab4:
    st.subheader("TCO vs. Annual Miles")

    available_vehicles = df.sort_values("TCO")["Label"].tolist()
    sens_sel = st.multiselect(
        "Select up to 8 vehicles",
        available_vehicles,
        default=available_vehicles[:5],
        key="sens_sel",
    )
    if len(sens_sel) > 8:
        st.warning("Select 8 or fewer vehicles for a readable chart.")
        sens_sel = sens_sel[:8]

    total_mi = city_mi + hwy_mi
    city_frac = city_mi / max(total_mi, 1)

    miles_min, miles_max = st.slider(
        "Annual miles range",
        500,
        30_000,
        (500, 20_000),
        step=500,
        key="sens_miles",
    )

    if not sens_sel:
        st.info("Select vehicles above.")
    else:
        mile_points = np.arange(miles_min, miles_max + 500, 500)
        r_sens = discount_pct / 100.0
        pv_factor_sens = (
            (1 - (1 + r_sens) ** (-years)) / r_sens if r_sens > 0 else float(years)
        )

        fig4 = go.Figure()
        sub_sens = df[df["Label"].isin(sens_sel)]
        for _, row in sub_sens.iterrows():
            tcos = []
            for mi in mile_points:
                c = mi * city_frac
                h = mi * (1 - city_frac)
                annual_fuel = (
                    c * row["Fuel_cost_city_per_mile"] + h * row["Fuel_cost_hwy_per_mile"]
                )
                annual_cost = annual_fuel + row["Annual_Insurance"] + row["Annual_Maint"]
                tco = row["Purchase"] + annual_cost * pv_factor_sens - row["PV_Resale"]
                tcos.append(tco)

            fig4.add_trace(
                go.Scatter(
                    x=list(mile_points),
                    y=tcos,
                    name=row["Label"],
                    mode="lines",
                    hovertemplate="%{x:,} mi/yr → $%{y:,.0f}<extra>"
                    + row["Label"]
                    + "</extra>",
                )
            )

        if miles_min <= total_mi <= miles_max:
            fig4.add_vline(
                x=total_mi,
                line_dash="dash",
                line_color="rgba(100,100,100,0.6)",
                annotation_text=f"Current: {total_mi:,} mi/yr",
                annotation_position="top right",
            )

        fig4.update_layout(
            height=560,
            xaxis_title="Total Annual Miles",
            yaxis_title="TCO ($)",
            yaxis_tickformat="$,.0f",
            xaxis_tickformat=",",
            legend_title="Vehicle",
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.caption(
            f"City/hwy split held at {city_frac:.0%}/{1-city_frac:.0%}. "
            "Resale held fixed at current ownership years."
        )

# ── Tab 5: Data Table ─────────────────────────────────────────────────────────

with tab5:
    display_cols = [
        "Label",
        "Year",
        "Make",
        "Model",
        "Trim",
        "Powertrain",
        "Purchase",
        "TCO",
        "Annual_Fuel",
        "Annual_Insurance",
        "Annual_Maint",
        "Resale_N",
        "IIHS_Rating",
        "RepairPal_5",
        "AWD_Standard",
        "AEB_Standard",
        "ACC_Standard",
        "Physical_HVAC_Controls",
        "Max_Cargo_cuft",
        "Cargo_2nd_Row_cuft",
    ]

    df_display = df[display_cols].sort_values("TCO").reset_index(drop=True)

    fmt_cols = ["Purchase", "TCO", "Annual_Fuel", "Annual_Insurance", "Annual_Maint", "Resale_N"]
    col_config = {
        "Label": st.column_config.TextColumn("Vehicle", width="large"),
    }
    for col in fmt_cols:
        col_config[col] = st.column_config.NumberColumn(
            col.replace("_", " ").replace("Annual ", "Annual "),
            format="$%.0f",
        )

    st.dataframe(df_display, use_container_width=True, hide_index=True, column_config=col_config)

    csv_bytes = df_display.to_csv(index=False)
    st.download_button(
        "⬇️ Download filtered data as CSV",
        csv_bytes,
        "tco_comparison.csv",
        "text/csv",
    )

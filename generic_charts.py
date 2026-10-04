"""
Generic chart builder — produces the same Tableau-style visual language
(KPI cards, bars, treemap, packed bubbles) from whatever numeric and
categorical columns a profiler found, regardless of column names.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from bubble_layout import packed_bubble_figure

# Tableau's classic "Tableau 10" categorical palette
TABLEAU10 = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
             "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"]


def build_generic_charts(df: pd.DataFrame, profile: dict, fig_to_div):
    charts = []
    num_cols = profile["numeric_cols"][:4]
    cat_cols = profile["categorical_cols"][:3]

    # 1. Distribution of each numeric column (up to 2 shown)
    for i, col in enumerate(num_cols[:2]):
        fig = px.histogram(df, x=col, nbins=20, color_discrete_sequence=[TABLEAU10[i]],
                            title=f"Distribution of {col}")
        fig.update_layout(bargap=0.05)
        charts.append({"id": f"num_{i}", "title": f"Distribution of {col}",
                        "html": fig_to_div(fig, f"chart-num-{i}")})

    # 2. Category counts (up to 2 categorical columns)
    for i, col in enumerate(cat_cols[:2]):
        vc = df[col].value_counts().reset_index()
        vc.columns = [col, "Count"]
        fig = px.bar(vc, x=col, y="Count", color=col, color_discrete_sequence=TABLEAU10,
                     title=f"Count by {col}")
        fig.update_layout(showlegend=False)
        charts.append({"id": f"cat_{i}", "title": f"Count by {col}",
                        "html": fig_to_div(fig, f"chart-cat-{i}")})

    # 3. Cross analysis — avg of first numeric by first categorical (faceted bar, Tableau-style)
    if num_cols and cat_cols:
        n_col, c_col = num_cols[0], cat_cols[0]
        grp = df.groupby(c_col)[n_col].mean().reset_index()
        fig = px.bar(grp, x=c_col, y=n_col, color=c_col, color_discrete_sequence=TABLEAU10,
                     title=f"Average {n_col} by {c_col}")
        fig.update_layout(showlegend=False)
        charts.append({"id": "cross", "title": f"Average {n_col} by {c_col}",
                        "html": fig_to_div(fig, "chart-cross")})

    # 4. Treemap — second categorical nested by first (or counts if only one)
    if len(cat_cols) >= 2:
        tv = df.groupby([cat_cols[0], cat_cols[1]]).size().reset_index(name="Count")
        fig = px.treemap(tv, path=[cat_cols[0], cat_cols[1]], values="Count",
                          color="Count", color_continuous_scale="Blues",
                          title=f"{cat_cols[0]} by {cat_cols[1]}")
        fig.update_layout(coloraxis_showscale=False)
        charts.append({"id": "treemap", "title": f"{cat_cols[0]} by {cat_cols[1]}",
                        "html": fig_to_div(fig, "chart-treemap")})
    elif num_cols and cat_cols:
        tv = df.groupby(cat_cols[0])[num_cols[0]].sum().reset_index()
        fig = px.treemap(tv, path=[cat_cols[0]], values=num_cols[0],
                          color=num_cols[0], color_continuous_scale="Blues",
                          title=f"{num_cols[0]} share by {cat_cols[0]}")
        fig.update_layout(coloraxis_showscale=False)
        charts.append({"id": "treemap", "title": f"{num_cols[0]} share by {cat_cols[0]}",
                        "html": fig_to_div(fig, "chart-treemap")})

    # 5. Packed bubble — category frequency (Tableau-style circle packing)
    if cat_cols:
        col = cat_cols[-1] if len(cat_cols) > 1 else cat_cols[0]
        vc = df[col].value_counts()
        fig = packed_bubble_figure(vc.index.astype(str).tolist(), vc.values.tolist(),
                                    colors=[TABLEAU10[i % 10] for i in range(len(vc))],
                                    title=f"{col} (packed bubble)")
        charts.append({"id": "bubble", "title": f"{col} (packed bubble)",
                        "html": fig_to_div(fig, "chart-bubble")})

    # 6. Trend line if a datetime column exists
    if profile["datetime_cols"] and num_cols:
        d_col, n_col = profile["datetime_cols"][0], num_cols[0]
        tmp = df.copy()
        tmp[d_col] = pd.to_datetime(tmp[d_col], errors="coerce", format="mixed")
        trend = tmp.dropna(subset=[d_col]).groupby(tmp[d_col].dt.date)[n_col].mean().reset_index()
        fig = px.line(trend, x=d_col, y=n_col, markers=True, color_discrete_sequence=[TABLEAU10[0]],
                      title=f"{n_col} over time")
        charts.append({"id": "trend", "title": f"{n_col} over time",
                        "html": fig_to_div(fig, "chart-trend")})

    return charts


def build_generic_kpis(df: pd.DataFrame, profile: dict):
    kpis = [{"label": "Rows in view", "value": len(df)}]
    for col in profile["numeric_cols"][:3]:
        val = df[col].mean()
        kpis.append({"label": f"Avg {col}", "value": round(val, 2) if pd.notna(val) else "-"})
    return kpis

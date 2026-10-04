import os
import uuid
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd

from data_prep import load_data, validate_columns, REQUIRED_COLUMNS, CSV_PATH
from suggestions import build_suggestions
from bubble_layout import packed_bubble_figure
from generic_prep import clean_generic
from generic_charts import build_generic_charts, build_generic_kpis
from generic_suggestions import build_generic_suggestions

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-render-env")

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
TEMPLATE = "plotly_white"

# Colors matched to the original Tableau dashboard
PINK, BLUE = "#F28B9B", "#3F6FA0"
TEAL, ORANGE = "#2A9D8F", "#E9843C"

DF_DEFAULT, META_DEFAULT = load_data(CSV_PATH)


# ---------------------------------------------------------------- helpers --

CHART_TITLES = {
    "breakfast": "Breakfast Consumption",
    "health_gender": "Health Category by Gender",
    "vitamins": "Vitamins Consumption by Gender",
    "greek": "Health vs Greek Food Consumption",
    "weight_exercise": "Weight vs Exercise Frequency",
    "eating_cook": "Eating Out vs Cooking Frequency",
    "life_rewarding": "People Feeling Healthy and Life Rewarded",
    "comfort": "Comfort Food Reasons",
    "risk": "Students by Risk Group",
}


def get_active_dataset():
    """Return (df, meta, label, schema) for whichever dataset this session is using.
    schema is 'food' (matches the known survey columns) or 'generic' (any other CSV)."""
    path = session.get("dataset_path")
    schema = session.get("dataset_schema")
    if path and os.path.exists(path):
        try:
            if schema == "food":
                df, meta = load_data(path)
            else:
                raw = pd.read_csv(path)
                df, meta = clean_generic(raw)
                schema = "generic"
            return df, meta, session.get("dataset_name", "Uploaded dataset"), schema
        except Exception:
            pass
    return DF_DEFAULT, META_DEFAULT, "Demo dataset (food_coded.csv)", "food"


def apply_filters(df, gender, risk, exercise):
    if gender and gender != "All":
        df = df[df["Gender_Label"] == gender]
    if risk and risk != "All":
        df = df[df["Risk_Group"] == risk]
    if exercise and exercise != "All":
        df = df[df["Exercise_Label"] == exercise]
    return df


def fig_to_div(fig, div_id):
    fig.update_layout(template=TEMPLATE, margin=dict(l=30, r=20, t=50, b=30),
                       font=dict(family="Segoe UI, Arial", size=12),
                       title_font_size=14)
    return pio.to_html(fig, include_plotlyjs=False, full_html=False,
                        div_id=div_id, config=PLOT_CONFIG)


def build_charts(df):
    charts = {}

    # 1. Breakfast Consumption — horizontal bar
    bc = df["Breakfast_Label"].value_counts().reindex(["Cereal", "Donut"]).fillna(0).reset_index()
    bc.columns = ["Breakfast", "Count"]
    fig = px.bar(bc, x="Count", y="Breakfast", orientation="h", color="Breakfast",
                 color_discrete_map={"Cereal": ORANGE, "Donut": ORANGE},
                 title="Breakfast Consumption")
    fig.update_traces(marker_color=ORANGE)
    fig.update_layout(showlegend=False)
    charts["breakfast"] = fig_to_div(fig, "chart-breakfast")

    # 2. Health Category by Gender — faceted bar (Healthy | Unhealthy)
    hg = df.groupby(["Health_Category", "Gender_Label"]).size().reset_index(name="Count")
    fig = px.bar(hg, x="Gender_Label", y="Count", color="Gender_Label",
                 facet_col="Health_Category",
                 color_discrete_map={"Female": PINK, "Male": BLUE},
                 title="Health Category by Gender")
    fig.update_layout(showlegend=False)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    charts["health_gender"] = fig_to_div(fig, "chart-health-gender")

    # 3. Vitamins Consumption by Gender — dual line across risk groups
    order = ["Low Risk", "Moderate Risk", "High Risk"]
    vg = (df.groupby(["Gender_Label", "Risk_Group"], observed=True)["Vitamins_Label"]
            .apply(lambda s: (s == "Yes").mean() * 100).reset_index(name="Pct"))
    fig = px.line(vg, x="Risk_Group", y="Pct", color="Gender_Label", markers=True,
                  category_orders={"Risk_Group": order},
                  color_discrete_map={"Female": PINK, "Male": BLUE},
                  title="Vitamins Consumption by Gender")
    fig.update_yaxes(range=[0, 100], title="% taking vitamins")
    charts["vitamins"] = fig_to_div(fig, "chart-vitamins")

    # 4. Health vs Greek Food Consumption — faceted bar
    gf = df.groupby(["Health_Category", "greek_food"]).size().reset_index(name="Count")
    fig = px.bar(gf, x="greek_food", y="Count", facet_col="Health_Category",
                 color="Health_Category", color_discrete_map={"Healthy": BLUE, "Unhealthy": ORANGE},
                 title="Health vs Greek Food Consumption")
    fig.update_layout(showlegend=False)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_xaxes(title="Greek food rating (1-5)")
    charts["greek"] = fig_to_div(fig, "chart-greek")

    # 5. Weight vs Exercise Frequency — treemap
    wt = df.dropna(subset=["Weight_Bin"]).groupby(["Weight_Bin", "Exercise_Label"], observed=True).size().reset_index(name="Count")
    if len(wt):
        fig = px.treemap(wt, path=["Weight_Bin", "Exercise_Label"], values="Count",
                          color="Count", color_continuous_scale="Reds",
                          title="Weight vs Exercise Frequency")
        fig.update_layout(coloraxis_showscale=False)
        charts["weight_exercise"] = fig_to_div(fig, "chart-weight-exercise")

    # 6. Eating Out vs Cooking Frequency — dual line
    eo = df["eating_out"].value_counts().sort_index()
    ck = df["cook"].value_counts().sort_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eo.index, y=eo.values, mode="lines+markers", name="Eating Out", line_color=TEAL))
    fig.add_trace(go.Scatter(x=ck.index, y=ck.values, mode="lines+markers", name="Cook", line_color=ORANGE))
    fig.update_layout(title="Eating Out vs Cooking Frequency", xaxis_title="Frequency scale (1-5)", yaxis_title="Students")
    charts["eating_cook"] = fig_to_div(fig, "chart-eating-cook")

    # 7. People Feeling Healthy and Life Rewarded — packed bubble
    lr = df["life_rewarding"].dropna().value_counts().sort_index()
    fig = packed_bubble_figure([str(int(i)) for i in lr.index], lr.values.tolist(),
                                colors=[TEAL] * len(lr), title="People Feeling Healthy and Life Rewarded")
    charts["life_rewarding"] = fig_to_div(fig, "chart-life-rewarding")

    # 8. Comfort Food Reasons — packed bubble
    cf = df["Comfort_Reason_Group"].value_counts()
    palette = {"Stress": "#8AC7D9", "Boredom": ORANGE, "Sadness": "#264653",
               "Happiness": TEAL, "None": "#C9A6D6", "Other": "#B0B0B0"}
    fig = packed_bubble_figure(cf.index.tolist(), cf.values.tolist(),
                                colors=[palette.get(k, "#999") for k in cf.index],
                                title="Comfort Food Reasons")
    charts["comfort"] = fig_to_div(fig, "chart-comfort")

    # 9. Risk group distribution (kept — supports the suggestion panel)
    rg = df["Risk_Group"].value_counts().reindex(["Low Risk", "Moderate Risk", "High Risk"]).fillna(0).reset_index()
    rg.columns = ["Risk_Group", "Count"]
    fig = px.bar(rg, x="Risk_Group", y="Count", color="Risk_Group",
                 color_discrete_map={"Low Risk": TEAL, "Moderate Risk": "#E9C46A", "High Risk": "#E63946"},
                 title="Students by Risk Group")
    fig.update_layout(showlegend=False)
    charts["risk"] = fig_to_div(fig, "chart-risk")

    return charts


# --------------------------------------------------------------- routes ---

@app.route("/")
def home():
    df, meta, label, schema = get_active_dataset()
    return render_template("index.html", meta=meta, dataset_label=label)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("dataset")
        if not file or file.filename == "":
            flash("Please choose a CSV file first.")
            return redirect(url_for("upload"))
        if not file.filename.lower().endswith(".csv"):
            flash("Only .csv files are supported.")
            return redirect(url_for("upload"))

        try:
            preview = pd.read_csv(file)
        except Exception as e:
            flash(f"Could not read that file as CSV: {e}")
            return redirect(url_for("upload"))

        if preview.empty or len(preview.columns) == 0:
            flash("That file has no readable rows or columns.")
            return redirect(url_for("upload"))

        missing = validate_columns(preview)
        schema = "food" if not missing else "generic"

        session_id = session.get("uid") or str(uuid.uuid4())
        session["uid"] = session_id
        save_path = os.path.join(UPLOAD_DIR, f"{session_id}.csv")
        preview.to_csv(save_path, index=False)
        session["dataset_path"] = save_path
        session["dataset_name"] = file.filename
        session["dataset_schema"] = schema

        if schema == "food":
            flash(f"Uploaded {file.filename} — recognized as a food-choices style dataset. Full dashboard applied.")
        else:
            flash(f"Uploaded {file.filename} — columns don't match the food-choices schema, so the platform "
                  f"auto-detected its structure and built a general dashboard from it instead.")
        return redirect(url_for("dashboard"))

    _, _, label, schema = get_active_dataset()
    return render_template("upload.html", current_label=label,
                            using_upload=bool(session.get("dataset_path")))


@app.route("/use-demo-data")
def use_demo_data():
    session.pop("dataset_path", None)
    session.pop("dataset_name", None)
    flash("Switched back to the demo dataset.")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    _, _, label, schema = get_active_dataset()
    return render_template("dashboard.html", dataset_label=label)


@app.route("/api/dashboard-meta")
def api_dashboard_meta():
    """Tells the frontend which filters to render, for whichever dataset is active."""
    df, meta, label, schema = get_active_dataset()
    if schema == "food":
        filters = [
            {"key": "gender", "label": "Gender", "options": ["All"] + sorted(df["Gender_Label"].dropna().unique().tolist())},
            {"key": "risk", "label": "Risk Group", "options": ["All", "Low Risk", "Moderate Risk", "High Risk"]},
            {"key": "exercise", "label": "Exercise", "options": ["All"] + sorted(df["Exercise_Label"].dropna().unique().tolist())},
        ]
    else:
        cat_cols = meta["profile"]["categorical_cols"][:2]
        filters = [
            {"key": f"cat{i}", "label": col, "options": ["All"] + sorted(df[col].dropna().astype(str).unique().tolist())}
            for i, col in enumerate(cat_cols)
        ]
    return jsonify({"filters": filters, "dataset_label": label, "schema": schema})


@app.route("/api/dashboard-data")
def api_dashboard_data():
    df, meta, label, schema = get_active_dataset()

    if schema == "food":
        gender = request.args.get("gender", "All")
        risk = request.args.get("risk", "All")
        exercise = request.args.get("exercise", "All")
        filtered = apply_filters(df, gender, risk, exercise)

        chart_dict = build_charts(filtered) if len(filtered) else {}
        charts = [{"id": k, "title": CHART_TITLES.get(k, k), "html": v} for k, v in chart_dict.items()]
        sugg = build_suggestions(filtered)
        kpis = [
            {"label": "Students in view", "value": len(filtered)},
            {"label": "Average GPA", "value": round(filtered["GPA"].mean(), 2) if len(filtered) else "-"},
            {"label": "Average weight (lb)", "value": round(filtered["Weight_Clean"].mean(), 1) if len(filtered) else "-"},
            {"label": "Grade Level (sum)", "value": int(filtered["grade_level"].sum()) if len(filtered) else "-"},
            {"label": "Avg. Healthy Eating Score", "value": round(filtered["Healthy_Eating_Score"].mean(), 1) if len(filtered) else "-"},
        ]
    else:
        cat_cols = meta["profile"]["categorical_cols"][:2]
        filtered = df.copy()
        for i, col in enumerate(cat_cols):
            val = request.args.get(f"cat{i}", "All")
            if val and val != "All":
                filtered = filtered[filtered[col].astype(str) == val]

        charts = build_generic_charts(filtered, meta["profile"], fig_to_div) if len(filtered) else []
        kpis = build_generic_kpis(filtered, meta["profile"])
        sugg = build_generic_suggestions(filtered, meta["profile"], meta["removed_nulls"])

    return jsonify({"charts": charts, "kpis": kpis, "suggestions": sugg,
                     "dataset_label": label, "schema": schema})


@app.route("/story")
def story():
    return render_template("story.html")


@app.route("/api/story-data/<scene>")
def api_story_data(scene):
    # The story is a fixed narrative built on the food-choices demo data,
    # independent of whatever dataset is currently uploaded for the dashboard.
    df = DF_DEFAULT
    if scene == "rahul":
        grp = df.groupby("Breakfast_Label")["Healthy_Eating_Score"].mean().reset_index()
        fig = px.bar(grp, x="Breakfast_Label", y="Healthy_Eating_Score", color="Breakfast_Label",
                     color_discrete_sequence=[TEAL, "#E76F51"],
                     title="Avg. Healthy Eating Score by Breakfast Choice")
        fig.update_layout(showlegend=False)
        return jsonify({"chart": fig_to_div(fig, "story-rahul")})

    if scene == "priya":
        cf = df["Comfort_Reason_Group"].value_counts().reset_index()
        cf.columns = ["Reason", "Count"]
        fig = px.bar(cf.sort_values("Count", ascending=True), x="Count", y="Reason", orientation="h",
                     color="Reason", color_discrete_sequence=px.colors.qualitative.Set2,
                     title="Why Students Reach for Comfort Food")
        fig.update_layout(showlegend=False)
        return jsonify({"chart": fig_to_div(fig, "story-priya")})

    if scene == "cafeteria":
        avg_fruit = df["fruit_day"].mean()
        avg_veg = df["veggies_day"].mean()
        donut_pct = (df["Breakfast_Label"] == "Donut").mean() * 100
        fig = go.Figure(go.Bar(
            x=["Fruit (avg/day)", "Vegetables (avg/day)", "Donut breakfast (%)"],
            y=[avg_fruit, avg_veg, donut_pct],
            marker_color=[TEAL, TEAL, "#E76F51"]))
        fig.update_layout(title="Cafeteria Signal: Produce Intake vs Fast/Sugary Choices")
        return jsonify({"chart": fig_to_div(fig, "story-cafeteria")})

    return jsonify({"chart": "<p>Unknown scene</p>"})


@app.route("/performance")
def performance():
    df, meta, label, schema = get_active_dataset()
    if schema == "food":
        n_viz = len(CHART_TITLES)
        filters = ["Gender", "Risk Group", "Exercise Frequency"]
        calc_fields = meta["calculated_fields"]
    else:
        n_viz = len(build_generic_charts(df, meta["profile"], fig_to_div)) if len(df) else 0
        filters = meta["profile"]["categorical_cols"][:2]
        calc_fields = ["(schema auto-detected — no fixed calculated fields; "
                        "numeric/categorical columns identified automatically)"]
    stats = {
        "dataset_label": label,
        "schema": schema,
        "raw_rows": meta["total_rows_raw"],
        "removed_nulls": meta["removed_nulls"],
        "rows_used": meta["rows_used"],
        "calculated_fields": calc_fields,
        "n_calculated_fields": len(meta["calculated_fields"]) if schema == "food" else 0,
        "n_visualizations": n_viz,
        "n_story_scenes": 3,
        "filters": filters,
    }
    return render_template("performance.html", stats=stats)


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

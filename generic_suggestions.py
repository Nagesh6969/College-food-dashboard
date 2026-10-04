"""
Generic suggestion engine — same take/avoid/watch idea as the
food-choices engine, but derived purely from statistics so it works on
any uploaded dataset: which group scores highest/lowest on a numeric
measure, and how much spread/missingness exists.
"""
import pandas as pd


def build_generic_suggestions(df: pd.DataFrame, profile: dict, removed_nulls: int) -> dict:
    take, avoid, watch = [], [], []
    num_cols = profile["numeric_cols"]
    cat_cols = profile["categorical_cols"]
    n = len(df)

    if removed_nulls > 0 and n > 0:
        pct = removed_nulls / (removed_nulls + n) * 100
        if pct > 10:
            watch.append(f"{pct:.0f}% of uploaded rows were empty or unusable and were dropped — check data collection.")

    if num_cols and cat_cols:
        n_col, c_col = num_cols[0], cat_cols[0]
        grp = df.groupby(c_col)[n_col].mean().dropna().sort_values()
        if len(grp) >= 2:
            low_group, low_val = grp.index[0], grp.iloc[0]
            high_group, high_val = grp.index[-1], grp.iloc[-1]
            take.append(f"'{high_group}' leads on average {n_col} ({high_val:.1f}) — worth highlighting as a strength.")
            avoid.append(f"'{low_group}' trails on average {n_col} ({low_val:.1f}) — a likely focus area.")

    for col in num_cols[:2]:
        s = df[col].dropna()
        if len(s) > 1 and s.mean() != 0:
            cv = s.std() / abs(s.mean())
            if cv > 0.6:
                watch.append(f"{col} varies widely across records (std/mean = {cv:.2f}) — consider segmenting further before drawing conclusions.")

    if not take and not avoid and not watch:
        take.append("No strong patterns flagged yet — try uploading more rows or check that categorical columns are meaningful groups.")

    return {"take": take, "avoid": avoid, "watch": watch, "n": n}

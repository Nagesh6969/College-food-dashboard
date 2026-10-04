"""
Suggestion Engine (rule-based)
-------------------------------
Reads the currently filtered dataframe and produces plain-language
"what to take / what not to take" recommendations. Rule-based rather
than ML so every recommendation is explainable in a review: a panel
member can ask "why did it suggest that?" and the answer is always a
visible threshold on a real column.
"""

import pandas as pd


def build_suggestions(df: pd.DataFrame) -> dict:
    if len(df) == 0:
        return {"take": [], "avoid": [], "watch": [], "n": 0}

    n = len(df)
    avg_fruit_veg = df["Fruit_Veg_Score"].mean()
    pct_low_exercise = (df["Exercise_Label"] == "Rarely").mean() * 100
    pct_no_vitamins = (df["Vitamins_Label"] == "No").mean() * 100
    pct_donut_breakfast = (df["Breakfast_Label"] == "Donut").mean() * 100
    pct_stress_eating = (df["Comfort_Reason_Group"] == "Stress").mean() * 100
    pct_sadness_eating = (df["Comfort_Reason_Group"] == "Sadness").mean() * 100
    pct_high_risk = (df["Risk_Group"] == "High Risk").mean() * 100
    avg_score = df["Healthy_Eating_Score"].mean()

    take, avoid, watch = [], [], []

    # ---- Fruit & vegetables ----
    if avg_fruit_veg < 6:
        avoid.append("Low daily fruit and vegetable intake across this group — packaged snacks are likely filling the gap.")
        take.append("Add at least one fruit and one vegetable serving to each main meal.")
    else:
        take.append("Fruit and vegetable intake is reasonable here — maintain the current variety.")

    # ---- Breakfast ----
    if pct_donut_breakfast > 15:
        avoid.append(f"{pct_donut_breakfast:.0f}% choose a pastry-style breakfast (e.g. donuts) — high sugar, low satiety.")
        take.append("Swap sugary breakfast items for whole grains, eggs, or fruit to sustain morning energy.")

    # ---- Exercise ----
    if pct_low_exercise > 20:
        avoid.append(f"{pct_low_exercise:.0f}% report rarely exercising, which compounds dietary risk.")
        take.append("Encourage at least 20–30 minutes of light activity most days (walking counts).")

    # ---- Vitamins ----
    if pct_no_vitamins > 45:
        watch.append(f"{pct_no_vitamins:.0f}% are not taking any vitamin supplement — worth a nutritionist check-in, not a blanket recommendation.")

    # ---- Stress / emotional eating ----
    if pct_stress_eating > 25:
        avoid.append(f"{pct_stress_eating:.0f}% turn to comfort food specifically under stress.")
        take.append("Offer a stress-eating alternative list (fruit, short walk, tea) during exam periods.")
    if pct_sadness_eating > 15:
        watch.append(f"{pct_sadness_eating:.0f}% associate comfort food with sadness — this is an emotional-wellbeing signal, not just a diet one; loop in student counselling if it persists.")

    # ---- Overall risk ----
    if pct_high_risk > 25:
        avoid.append(f"{pct_high_risk:.0f}% of this group falls in the High Risk eating category.")
        take.append("Prioritize this segment for a targeted wellness or nutrition workshop first.")
    elif avg_score >= 65:
        take.append("Overall Healthy Eating Score is solid for this group — reinforce with recognition rather than intervention.")

    return {
        "take": take,
        "avoid": avoid,
        "watch": watch,
        "n": n,
        "avg_score": round(avg_score, 1),
        "avg_fruit_veg": round(avg_fruit_veg, 1),
        "pct_high_risk": round(pct_high_risk, 1),
    }

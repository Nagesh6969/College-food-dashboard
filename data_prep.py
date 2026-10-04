"""
Data Preparation Layer
-----------------------
Loads the raw food_coded.csv survey data, cleans it, and builds the
calculated fields used across the dashboard, story and suggestion engine.

Calculated fields created here (equivalent to Tableau calculated fields):
  - Gender_Label        : 1/2 codes -> Female/Male
  - Breakfast_Label      : 1/2 codes -> Cereal/Donut
  - Exercise_Label       : 1/2/3 codes -> Regularly/Sometimes/Rarely
  - Weight_Clean         : messy text weight column -> numeric pounds
  - Fruit_Veg_Score      : fruit_day + veggies_day (2-10 scale)
  - Healthy_Eating_Score : weighted score from fruit/veg intake,
                           vitamins, breakfast choice and exercise
  - Risk_Group           : Healthy_Eating_Score bucketed into
                           High / Moderate / Low risk
  - Comfort_Reason_Group : free-text comfort_food_reasons -> single
                           category (Stress, Boredom, Sadness, Happiness, None)
"""

import re
import pandas as pd
import numpy as np

CSV_PATH = "data/food_coded.csv"

# Columns the pipeline needs to compute the calculated fields. An uploaded
# file is validated against this list before it is accepted.
REQUIRED_COLUMNS = [
    "GPA", "Gender", "breakfast", "weight", "fruit_day", "veggies_day",
    "vitamins", "exercise", "comfort_food_reasons", "grade_level",
    "life_rewarding", "greek_food", "eating_out", "cook",
]


def validate_columns(df: pd.DataFrame):
    """Return list of missing required columns (empty list = valid)."""
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]

GENDER_MAP = {1: "Female", 2: "Male"}
BREAKFAST_MAP = {1: "Cereal", 2: "Donut"}
EXERCISE_MAP = {1: "Regularly", 2: "Sometimes", 3: "Rarely"}
VITAMIN_MAP = {1: "Yes", 2: "No"}

REASON_KEYWORDS = [
    ("Stress", ["stress", "anx", "school", "finals", "exam"]),
    ("Boredom", ["bored"]),
    ("Sadness", ["sad", "depress", "upset", "anger", "angry", "lonely"]),
    ("Happiness", ["happ", "celebrat", "reward"]),
]


def _clean_weight(val):
    """Extract the first numeric group from a messy weight entry."""
    if pd.isna(val):
        return np.nan
    m = re.search(r"(\d{2,3})", str(val))
    return float(m.group(1)) if m else np.nan


def _classify_reason(text):
    if pd.isna(text):
        return "None"
    t = str(text).lower()
    if "we dont have" in t or "don't eat" in t or "no comfort" in t or "none" in t:
        return "None"
    for label, keys in REASON_KEYWORDS:
        if any(k in t for k in keys):
            return label
    return "Other"


def load_data(path: str = CSV_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)

    # ---- Cleaning: drop rows with no usable dietary signal ----
    before = len(df)
    df["GPA"] = pd.to_numeric(df["GPA"], errors="coerce")
    df["Weight_Clean"] = df["weight"].apply(_clean_weight)

    key_cols = ["fruit_day", "veggies_day", "vitamins", "exercise", "breakfast"]
    df = df.dropna(subset=key_cols).reset_index(drop=True)
    removed_nulls = before - len(df)

    # ---- Calculated fields (Tableau-equivalent) ----
    df["Gender_Label"] = df["Gender"].map(GENDER_MAP)
    df["Breakfast_Label"] = df["breakfast"].map(BREAKFAST_MAP)
    df["Exercise_Label"] = df["exercise"].map(EXERCISE_MAP)
    df["Vitamins_Label"] = df["vitamins"].map(VITAMIN_MAP)
    df["Fruit_Veg_Score"] = df["fruit_day"] + df["veggies_day"]

    # Healthy Eating Score (0-100): weighted blend of positive habits
    exercise_points = df["exercise"].map({1: 3, 2: 2, 3: 0})
    vitamin_points = df["vitamins"].map({1: 2, 2: 0})
    breakfast_points = df["breakfast"].map({1: 2, 2: 0})
    raw_score = (
        df["Fruit_Veg_Score"] * 3
        + exercise_points * 5
        + vitamin_points * 5
        + breakfast_points * 5
    )
    df["Healthy_Eating_Score"] = (
        (raw_score - raw_score.min()) / (raw_score.max() - raw_score.min()) * 100
    ).round(1)

    df["Risk_Group"] = pd.cut(
        df["Healthy_Eating_Score"],
        bins=[-1, 40, 70, 101],
        labels=["High Risk", "Moderate Risk", "Low Risk"],
    )

    df["Comfort_Reason_Group"] = df["comfort_food_reasons"].apply(_classify_reason)

    df["Health_Category"] = np.where(
        df["Healthy_Eating_Score"] >= 55, "Healthy", "Unhealthy"
    )

    # Weight bins for the treemap (mirrors the Tableau "Weight vs Exercise" view)
    df["Weight_Bin"] = pd.cut(
        df["Weight_Clean"],
        bins=[0, 120, 140, 160, 180, 200, 400],
        labels=["<120", "120-140", "140-160", "160-180", "180-200", "200+"],
    )

    meta = {
        "total_rows_raw": before,
        "removed_nulls": removed_nulls,
        "rows_used": len(df),
        "calculated_fields": [
            "Gender_Label", "Breakfast_Label", "Exercise_Label", "Vitamins_Label",
            "Fruit_Veg_Score", "Healthy_Eating_Score", "Risk_Group",
            "Comfort_Reason_Group", "Health_Category", "Weight_Clean",
        ],
    }
    return df, meta


if __name__ == "__main__":
    df, meta = load_data()
    print(meta)
    print(df[["Gender_Label", "Healthy_Eating_Score", "Risk_Group", "Comfort_Reason_Group"]].head(10))

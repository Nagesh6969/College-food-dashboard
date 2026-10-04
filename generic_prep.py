"""
Generic Data Profiler
----------------------
Used when an uploaded CSV does NOT match the food-choices schema.
Instead of assuming what any column means, this inspects the actual
values and classifies each column as numeric, categorical, datetime,
an identifier (skip), or free text (skip) — the same thing a human
would do before building a Tableau worksheet from an unfamiliar file.
"""

import pandas as pd
import numpy as np


def profile_dataframe(df: pd.DataFrame) -> dict:
    n = len(df)
    numeric_cols, categorical_cols, datetime_cols, id_like, text_cols = [], [], [], [], []

    for col in df.columns:
        s = df[col]
        nunique = s.nunique(dropna=True)
        name_l = str(col).lower()

        # identifier-like: name says so, OR it's a sequential integer key
        # (NOT just "every value happens to be unique" — a continuous
        # measure like revenue is unique in a small sample but is not an ID)
        name_is_id = name_l in ("id", "index") or name_l.endswith("_id") or name_l.endswith("id")
        is_sequential_int = (
            pd.api.types.is_integer_dtype(s)
            and nunique == n
            and n > 3
            and s.sort_values().reset_index(drop=True).diff().dropna().eq(1).all()
        )
        if n > 10 and (name_is_id or is_sequential_int):
            id_like.append(col)
            continue

        if pd.api.types.is_numeric_dtype(s):
            numeric_cols.append(col)
            continue

        # try datetime (covers numpy object dtype AND pandas' newer
        # string dtype backend, which is not == object but also not numeric)
        try:
            parsed = pd.to_datetime(s, errors="coerce", format="mixed")
            if parsed.notna().mean() > 0.8:
                datetime_cols.append(col)
                continue
        except Exception:
            pass

        # low-cardinality text -> categorical
        if nunique <= 25 and nunique >= 1:
            categorical_cols.append(col)
        else:
            text_cols.append(col)

    return {
        "row_count": n,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "datetime_cols": datetime_cols,
        "id_like_cols": id_like,
        "text_cols": text_cols,
    }


def clean_generic(df: pd.DataFrame):
    before = len(df)
    df = df.dropna(how="all").reset_index(drop=True)
    # drop fully-empty columns
    df = df.dropna(axis=1, how="all")
    removed = before - len(df)
    profile = profile_dataframe(df)
    meta = {
        "total_rows_raw": before,
        "removed_nulls": removed,
        "rows_used": len(df),
        "calculated_fields": [],
        "profile": profile,
    }
    return df, meta

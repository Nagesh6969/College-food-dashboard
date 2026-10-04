# Comprehensive Analysis and Dietary Strategies with Tableau
### (Flask + Plotly implementation — deployable, with dataset upload)

## What's new in this version
- **Charts rebuilt to match the original Tableau dashboard** — treemap for
  Weight vs Exercise, packed-bubble charts for Comfort Food Reasons and
  People Feeling Healthy, faceted bars for Health Category by Gender and
  Health vs Greek Food, dual-line Eating Out vs Cooking, and the same KPI
  card fields (Count, Avg GPA, Avg Weight, Grade Level).
- **Dataset upload** — anyone can upload their own `food_coded.csv`-style
  file at `/upload`. The platform validates required columns, re-runs the
  full cleaning + calculated-field pipeline on it, and every chart, the
  story and the suggestion engine switch to that data — per browser
  session, so two people using the deployed site at once don't see each
  other's uploads.
- **Deployment-ready** for Render.com (Procfile, gunicorn, runtime.txt).

## Run it locally
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Deploy to Render.com (free tier) — step by step

1. **Push this folder to GitHub**
   - Create a new repository on github.com (public or private, either works).
   - In this folder, run:
     ```
     git init
     git add .
     git commit -m "Initial deploy"
     git branch -M main
     git remote add origin https://github.com/<your-username>/<repo-name>.git
     git push -u origin main
     ```

2. **Create the Render service**
   - Go to https://render.com and sign up / log in (GitHub login is easiest).
   - Click **New +** -> **Web Service**.
   - Connect your GitHub account, pick the repository you just pushed.

3. **Configure the service** (Render auto-detects most of this, but confirm):
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free

4. **Add an environment variable**
   - Under the service's **Environment** tab, add:
     - Key: `SECRET_KEY`
     - Value: any random string, e.g. generate one with
       `python -c "import secrets; print(secrets.token_hex(16))"`
   - This keeps upload sessions secure; without it Flask falls back to a
     dev key, which still works but isn't safe for a public deploy.

5. **Deploy**
   - Click **Create Web Service**. Render builds and deploys automatically
     — first deploy takes 2-5 minutes.
   - You'll get a public URL like `https://your-app-name.onrender.com`.

6. **Re-deploying after changes**
   - Just `git push` again — Render redeploys automatically on every push
     to the connected branch.

### Note on the free tier
Render's free web services spin down after ~15 minutes of no traffic and
take 30-60 seconds to wake back up on the next visit. Mention this if
you're demoing live to a panel so a slow first load doesn't look like a bug.

### Note on uploaded files
Render's free tier has an ephemeral filesystem — uploaded CSVs in
`data/uploads/` are wiped whenever the service restarts or spins down.
Fine for a demo/review tool; not meant as permanent storage.

## Pages
- `/`            Overview — dataset stats and calculated fields
- `/upload`      Upload a CSV; validated and swapped in as the active dataset
- `/dashboard`   Interactive dashboard — filter by gender, risk group,
                 exercise; 9 charts and suggestions update live
- `/story`       3 narrative scenes (Rahul, Priya, Cafeteria Manager)
- `/performance` Performance testing numbers pulled from the active dataset

## Calculated fields
- Healthy_Eating_Score — 0-100 weighted score from fruit/veg, exercise, vitamins, breakfast
- Risk_Group — Low / Moderate / High Risk, bucketed from the score
- Fruit_Veg_Score — fruit_day + veggies_day
- Comfort_Reason_Group — free text -> Stress / Boredom / Sadness / Happiness / None
- Weight_Bin — binned weight ranges, used by the treemap
- Gender_Label, Breakfast_Label, Exercise_Label, Vitamins_Label, Health_Category, Weight_Clean

## Suggestion engine logic
Rule-based, not ML — every "take / avoid / watch" line is tied to a visible
threshold on a real column (e.g. "avoid" fires when donut-breakfast rate
exceeds 15% of the filtered group), so it's fully explainable to a panel.

## Required columns for an uploaded CSV
GPA, Gender, breakfast, weight, fruit_day, veggies_day, vitamins, exercise,
comfort_food_reasons, grade_level, life_rewarding, greek_food, eating_out, cook

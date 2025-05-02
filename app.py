from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error = None
    form = request.form

    if request.method == "POST":
        try:
            df = pd.read_csv("credit_cards.csv").fillna("")

            # --- Form Inputs ---
            credit_score = request.form.get("credit_score", type=int) or 690
            is_new = form.get("is_new", "No")
            banks = form.getlist("banks[]")
            five_twentyfour = form.get("five_twentyfour", "No")
            has_sapphire = form.get("has_sapphire", "No")
            open_to_fee = form.get("open_to_fee", "Yes")
            wants_travel = form.get("wants_travel_card", "No")
            spend_groceries = request.form.get("spend_groceries", type=int) or 0
            spend_dining = request.form.get("spend_dining", type=int) or 0
            spend_travel = request.form.get("spend_travel", type=int) or 0

            # --- Normalize columns ---
            df["annual_fee"] = pd.to_numeric(df["annual_fee"], errors="coerce").fillna(0)
            df["min_credit_score"] = pd.to_numeric(df["min_credit_score"], errors="coerce").fillna(0)
            for col in ["rewards_groceries", "rewards_dining", "rewards_travel"]:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            # --- Filtering Logic ---
            flexible_issuers = ["Capital One", "Discover"]
            eligible = df[
                (df["issuer"].isin(flexible_issuers)) |
                (df["min_credit_score"] <= credit_score)
            ]

            if open_to_fee == "No":
                eligible = eligible[eligible["annual_fee"] == 0]

            if five_twentyfour == "Yes":
                eligible = eligible[~((eligible["issuer"] == "Chase") & (eligible["is_524_sensitive"] == "Yes"))]

            if is_new == "Yes":
                eligible = eligible[eligible["beginner_friendly"] == "Yes"]

            if wants_travel == "Yes":
                eligible = eligible[eligible["premium_travel_card"] == "Yes"]

            if eligible.empty:
                error = "😕 We couldn't find any recommendations based on your inputs."
                return render_template("index.html", form=form, results=[], error=error)

            # --- Scoring ---
            def score_card(row):
                score = (
                    row["rewards_groceries"] * spend_groceries +
                    row["rewards_dining"] * spend_dining +
                    row["rewards_travel"] * spend_travel
                ) * 12 - row["annual_fee"]

                if is_new == "Yes" and row["beginner_friendly"] == "Yes" and row["issuer"] in banks:
                    score += 100
                return score

            eligible["score"] = eligible.apply(score_card, axis=1)
            eligible = eligible.sort_values(by="score", ascending=False).head(5)
            results = eligible.to_dict(orient="records")

            # --- Warnings ---
            for card in results:
                card["warnings"] = []
                if card.get("sapphire_sub_lock") == "Yes":
                    if has_sapphire == "Yes":
                        card["warnings"].append("🕒 You have a Sapphire card. No new bonus for 48 months.")
                    elif has_sapphire == "Maybe":
                        card["warnings"].append("🤔 Sapphire bonus may be restricted if held in past 48 months.")
                if card.get("sapphire_hold_lock") == "Yes":
                    card["warnings"].append("🚫 You can't hold two Sapphire cards.")
        except Exception as e:
            error = f"Something went wrong: {str(e)}"

    return render_template("index.html", form=form, results=results, error=error)

@app.route("/support")
def support():
    return render_template("support.html")

if __name__ == "__main__":
    app.run(debug=True)


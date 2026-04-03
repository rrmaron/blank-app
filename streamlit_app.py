# app.py — FIDE Initial Rating Calculator — Rating only after 5 real games

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import base64
import csv

# Auto-install reportlab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
except ImportError:
    st.error("Installing reportlab...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import inch

# ====================== FIDE dp TABLE ======================
def fide_dp_table():
    return {1.00:800,0.99:677,0.98:589,0.97:538,0.96:501,0.95:470,0.94:444,0.93:422,0.92:401,0.91:383,
            0.90:366,0.89:351,0.88:336,0.87:322,0.86:309,0.85:296,0.84:284,0.83:273,0.82:262,0.81:251,
            0.80:240,0.79:230,0.78:220,0.77:211,0.76:202,0.75:193,0.74:184,0.73:175,0.72:166,0.71:158,
            0.70:149,0.69:141,0.68:133,0.67:125,0.66:117,0.65:110,0.64:102,0.63:95,0.62:87,0.61:80,
            0.60:72,0.59:65,0.58:57,0.57:50,0.56:43,0.55:36,0.54:29,0.53:21,0.52:14,0.51:7,0.50:0,
            0.49:-7,0.48:-14,0.47:-21,0.46:-29,0.45:-36,0.44:-43,0.43:-50,0.42:-57,0.41:-65,0.40:-72,
            0.39:-80,0.38:-87,0.37:-95,0.36:-102,0.35:-110,0.34:-117,0.33:-125,0.32:-133,0.31:-141,
            0.30:-149,0.29:-158,0.28:-166,0.27:-175,0.26:-184,0.25:-193,0.24:-202,0.23:-211,0.22:-220,
            0.21:-230,0.20:-240,0.19:-251,0.18:-262,0.17:-273,0.16:-284,0.15:-296,0.14:-309,0.13:-322,
            0.12:-336,0.11:-351,0.10:-366,0.09:-383,0.08:-401,0.07:-422,0.06:-444,0.05:-470,0.04:-501,
            0.03:-538,0.02:-589,0.01:-677,0.00:-800}

def get_dp(p):
    table = fide_dp_table()
    p_rounded = round(p, 2)
    for threshold in sorted(table.keys(), reverse=True):
        if p_rounded >= threshold:
            return table[threshold]
    return -800

# ====================== CALCULATION ======================

def calculate_rating(opponents, results):
    """
    Calculate FIDE initial rating from list of opponent ratings and results.
    Handles both numeric and string results from CSV/editable table.
    Ignores invalid rows.
    """
    # Filter valid pairs
    valid_opponents = []
    valid_results = []

    for opp, res in zip(opponents, results):
        # Skip invalid opponent rating
        try:
            opp_val = float(opp)
            if pd.isna(opp_val) or not opp_val.is_integer() or opp_val < 800 or opp_val > 3000:
                continue
            opp_val = int(opp_val)
        except (ValueError, TypeError):
            continue

        # Handle result (numeric or string)
        try:
            res_val = float(res)
            if pd.isna(res_val):
                continue
            if res_val == 1.0 or res_val == 1:
                score_add = 1.0
            elif res_val == 0.5:
                score_add = 0.5
            else:
                score_add = 0.0  # loss or other
        except (ValueError, TypeError):
            # Fallback to string
            res_str = str(res).strip().lower()
            if res_str in ["1", "1.0", "win"]:
                score_add = 1.0
            elif res_str in ["0.5", "0,5", "½", "draw", "="]:
                score_add = 0.5
            else:
                score_add = 0.0  # loss, invalid, or "0"

        valid_opponents.append(opp_val)
        valid_results.append(score_add)

    # If not enough valid games
    if len(valid_opponents) < 5:
        return None

    games = len(valid_opponents) + 2
    avg = (sum(valid_opponents) + 3600) // games
    score = sum(valid_results) + 1
    perc = score / games
    dp = get_dp(perc)
    Rp = avg + dp
    rating = max(Rp, 1000)

    if avg >= 2000 and perc >= 0.50:
        rating = max(rating, 1600)
    if Rp >= 2250:
        rating = max(rating, 1800)
    if Rp >= 2400:
        rating = max(rating, 2000)

    return {
        "rating": round(rating),
        "Rp": round(Rp),
        "avg": avg,
        "score": score,
        "games": games,
        "perc": round(perc * 100, 1),
        "dp": dp
    }



# ====================== PDF GENERATOR ======================
def generate_pdf(data, name):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*inch)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("FIDE Initial Rating Certificate",
                          ParagraphStyle('Title', parent=styles['Title'], fontSize=36, alignment=1, spaceAfter=60, textColor="#003087")))
    story.append(Paragraph(f"<b>{name or 'Chess Player'}</b>", ParagraphStyle('Name', fontSize=28, alignment=1, spaceAfter=40)))
    story.append(Paragraph(f"<font size=90><b>{data['rating']}</b></font>",
                          ParagraphStyle('Rating', alignment=1, textColor="#003087")))
    story.append(Paragraph("First Official FIDE Rating", ParagraphStyle('Sub', fontSize=22, alignment=1, spaceAfter=60)))
    t = Table([
        ["Games Played", str(data['games'])],
        ["Average Opponent", str(data['avg'])],
        ["Score", f"{data['score']}/{data['games']} ({data['perc']}%)"],
        ["Performance Rating", str(data['Rp'])],
        ["Date", datetime.now().strftime("%B %d, %Y")],
    ], colWidths=[3.8*inch, 2.8*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),"#003087"), ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),2,colors.lightgrey), ('BACKGROUND',(0,1),(-1,-1),"#f0f8ff"),
        ('FONTSIZE',(0,0),(-1,-1),16), ('LEFTPADDING',(0,0),(-1,-1),30),
    ]))
    story.append(t)
    story.append(Spacer(1, 60))
    story.append(Paragraph("Per FIDE Rating Regulations effective March 1, 2024", ParagraphStyle('Footer', alignment=1, fontSize=14, textColor="#555")))
    doc.build(story)
    buffer.seek(0)
    return buffer

# ====================== STREAMLIT APP ======================
st.set_page_config(page_title="FIDE Rating Pro", page_icon="Trophy", layout="centered")

st.markdown("<h1 style='text-align: center; color: #003087;'>FIDE Initial Rating Calculator</h1>", unsafe_allow_html=True)

# === DEFAULT GAMES ===
default_games = pd.DataFrame([
    {"Opponent Rating": 1800, "Result": "0.5"},
    {"Opponent Rating": 1800, "Result": "0.5"}
])

if "games" not in st.session_state:
    st.session_state.games = default_games.copy()

# === CALCULATE RATING ONLY FROM REAL GAMES ===
real_games = st.session_state.games.iloc[2:] if len(st.session_state.games) > 2 else pd.DataFrame(columns=["Opponent Rating", "Result"])

rating_result = calculate_rating(
    real_games["Opponent Rating"].tolist(),
    real_games["Result"].tolist()
) if not real_games.empty else None

# === RATING UNDER HEADING ===
if rating_result and len(real_games) >= 5:
    st.markdown(f"<h2 style='text-align: center; color: #003087;'>Your First FIDE Rating: <b>{rating_result['rating']}</b></h2>", unsafe_allow_html=True)
else:
    st.markdown("<h2 style='text-align: center; color: #888;'>Your First FIDE Rating: <i>Not yet available (need 5+ real games)</i></h2>", unsafe_allow_html=True)


# === EXPLANATORY PARAGRAPH ===
st.markdown("""
<p style='text-align: left; color: #555; font-size: 1.1em; margin: 0 0 1rem 0;'>
To calculate the initial rating, it starts with 2 draws against fictional opponents that have a 1800 rating — these are prefilled below.<br>
Then we need 5 more results against FIDE-rated opponents to get your first official rating. <br>
If you score 0 points in your first tournament, your results are disregarded and do not count toward your initial rating. <br>
Only start entering results from a tournament in which you have at least drawn against a FIDE rated opponent <br>
If you have lost your FIDE rating (gone below 1400), then you have to start again from the beginning and would need a minimum of 5 games again with at least 0.5 points to get a rating
<br>
FIDE Rating Regulations, effective March 1, 2024 - https://handbook.fide.com/chapter/B022024 <br>
The relevant points for unrated players are as follows: <br>
<br>
6.1 Matches in which one player is unrated shall not be rated. <br>

7.1.4 A rating for a player new to the list shall be published when it is based on at least 5 games against rated opponents. This need not be met in one tournament. Results from other tournaments played within consecutive rating periods of not more than 26 months are pooled to obtain the initial rating. The rating must be at least 1400.
<br>
8.2.1 If an unrated player scores zero in their first event this score is disregarded. Otherwise, their rating is calculated using all their results as in 7.1.4.
<br>
<br>
Use the "Add Game" box below to add any games played against FIDE opponents.   
<br> Can get your older games from the FIDE site  <a href="https://ratings.fide.com/">Fide Ratings Site</a>  
Put in your name and search and when your find your name,  Go to "Calculations" and go each month played and "View"
</p><br>
Please note that FIDE ratings will only show up on or after the first of the month, so if you earned your FIDE rating in early March, it will only show up as an official FIDE rating on or after April 1st.  FIDE uses a calendar month period and does not give out ratings after every tournament. 
<br> Link to the official FIDE calculator <a href="https://ratings.fide.com/calc.phtml?page=change">Fide Calculators</a> <br>
Once you have a FIDE rating, then use the official <a href="https://ratings.fide.com/calc.phtml?page=change">Fide Calculator - Rating Change in white</a> to see how your rating will change depending on your opponents rating and the result (win, lose or draw),  
""", unsafe_allow_html=True)

st.markdown("---")



# === QUICK ADD GAME ===
with st.expander("Add Game", expanded=True):
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        rating = st.number_input("Opponent Rating", 800, 3000, 1500, step=1)
    with c2:
        result = st.selectbox("Result", ["1 (Win)", "0.5 (Draw)", "0 (Loss)"])
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add", type="primary", width='stretch'):
            new_row = pd.DataFrame([{"Opponent Rating": rating, "Result": "1" if "Win" in result else "0.5" if "Draw" in result else "0"}])
            st.session_state.games = pd.concat([st.session_state.games, new_row], ignore_index=True)
            st.success("Game added!")
            st.rerun()

# === CSV IMPORT — Auto-clear uploader, no "X" needed ===
st.download_button("Download CSV Template", data="opponent_rating,result\n1800,0.5\n1800,0.5\n", file_name="fide_template.csv", mime="text/csv")

# Unique key for uploader to force refresh after upload
uploaded_key = f"uploader_{st.session_state.get('upload_counter', 0)}"
uploaded = st.file_uploader(
    "Upload CSV (will replace current games)",
    type=["csv"],
    key=uploaded_key
)

if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)
        if {"opponent_rating", "result"}.issubset(set(df.columns.str.lower())):
            df = df.rename(columns=str.lower)
            df["Opponent Rating"] = df["opponent_rating"].astype(int)
            df["Result"] = df["result"].astype(str)
            st.session_state.games = df[["Opponent Rating", "Result"]].copy()
            
            # Clear the uploader widget and increment key
            st.session_state.uploaded = None
            st.session_state.upload_counter = st.session_state.get('upload_counter', 0) + 1
            
            # Non-blocking success
            st.toast(f"Imported {len(df)} games successfully!", icon="✅")
            
            # Force immediate refresh so table shows new data
            st.rerun()
        else:
            st.error("CSV must have: opponent_rating, result")
    except Exception as e:
        st.error(f"Error: {e}")

# === EDITABLE TABLE ===
st.subheader(f"Your Real Games ({len(st.session_state.games)-2}) Please don't delete the 2 games with draws for 1800 players as that is part of the FIDE calculation")
edited = st.data_editor(
    st.session_state.games,
    num_rows="dynamic",
    width='stretch',
    column_config={
        "Opponent Rating": st.column_config.NumberColumn("Opponent Rating", min_value=800, max_value=3000, step=1),
        "Result": st.column_config.SelectboxColumn("Result", options=["1", "0.5", "0"], default="0.5")
    },
    hide_index=False
)

# === IMMEDIATE RECALCULATION ON EDIT ===
if not edited.equals(st.session_state.games):
    st.session_state.games = edited.copy()
    st.success("Changes saved — rating updated!")
    st.rerun()  # Re-run to recalculate and refresh display
    
if not edited.equals(st.session_state.games):
    st.session_state.games = edited.copy()
    st.success("Changes saved!")

col1, col2 = st.columns(2)
with col1:
    if st.button("Clear All Games"):
        st.session_state.games = default_games.copy()
        st.rerun()
with col2:
    export_df = st.session_state.games.copy()
    export_df = export_df.rename(columns={
        "Opponent Rating": "opponent_rating",
        "Result": "result"
    })
    
    export_df["result"] = export_df["result"].astype(str).replace({
        "0": "0",       # explicit string "0"
        "0.0": "0",
        "0.5": "0.5",
        "1": "1",
        "1.0": "1"
    })


    
    csv = export_df.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC)
    
    st.download_button("Export CSV", csv, "my_fide_games.csv", "text/csv", help="Downloads your current games - Result column preserved as text")


    
# === DETAILED RATING (only if 5+ real games) ===
if rating_result and len(real_games) >= 5:
    st.write(f"Performance/Initial Rating: {rating_result['Rp']} = Average opponent rating + dp (dp is usually negative,so subtracted) = {rating_result['avg']} + {rating_result['dp']:-}.  The official FIDE calculation includes the 2 imaginary draws against 1800 rated opponents, so that's why number of games is shown as 2 higher than the real number played ")
    c1, c2, c3 = st.columns(3)
    c1.metric("Games", rating_result['games'])
    c2.metric("Score %", f"{rating_result['perc']}%")
    c3.metric("Avg Opponent", rating_result['avg'])
    

    
    name = st.text_input("Your Name", placeholder="e.g. Your Name")
    if st.button("Download PDF Certificate", type="primary"):
        pdf = generate_pdf(rating_result, name or "Chess Player")
        b64 = base64.b64encode(pdf.read()).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="FIDE_Rating_{rating_result["rating"]}.pdf">Download Certificate</a>'
        st.markdown(href, unsafe_allow_html=True)
        st.balloons()
else:
    st.info(f"Need 5+ real games against FIDE rated opponents to calculate rating • You have {len(real_games)} real games")

st.caption("Starts with 2 default games • Edit freely • 100% free")

st.caption("FIDE K-Factor Rules (Effective March 2024):K=40: Players new to the rating list until they complete 30 games.K=40: Players under 18 years old until their rating reaches 2300.K=20: Players with a rating below 2400.K=10: Players whose published rating reaches 2400 or higher, even if it later falls below that level.Special Note: For rapid and blitz, a K-factor of 20 is generally used")

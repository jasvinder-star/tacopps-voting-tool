import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import statistics
import os

# =============================================
# CONFIGURATION
# =============================================
ADMIN_PASSWORD = "bxic2024"
RECIPIENT_EMAIL = "khaira@blackstone.com"

DESCRIPTORS = {
    1: "Hard pass — I wouldn't touch this with a 10-foot DCF",
    2: "Did an intern build this model on a napkin?",
    3: "Creative use of the word 'adjusted'",
    4: "I've seen better risk/reward at the Bellagio",
    5: "It's a deal. That's the nicest thing I can say.",
    6: "Wouldn't kick it out of the pipeline",
    7: "Solid — I'd bring it up at partner dinner",
    8: "Allocating my PA immediately",
    9: "Calling my FA to liquidate everything",
    10: "Leveraging my 401k and calling my mother's financial advisor",
}

SCORE_COLORS = {
    1: "#d32f2f",
    2: "#c62828",
    3: "#e65100",
    4: "#ef6c00",
    5: "#f9a825",
    6: "#9e9d24",
    7: "#558b2f",
    8: "#2e7d32",
    9: "#1b5e20",
    10: "#004d40",
}

# =============================================
# PAGE CONFIG
# =============================================
st.set_page_config(
    page_title="IC Conviction Vote",
    page_icon=None,
    layout="centered",
)

# =============================================
# CUSTOM CSS
# =============================================
st.markdown(
    """
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
    }

    /* Header styling */
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        border-bottom: 2px solid #2d2d5e;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: #e0e0e0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 0.3rem;
    }
    .main-header p {
        color: #8888aa;
        font-size: 1rem;
    }

    /* Deal name banner */
    .deal-banner {
        background: linear-gradient(90deg, #1a237e, #283593);
        border: 1px solid #3949ab;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    .deal-banner h2 {
        color: #ffffff;
        font-size: 1.8rem;
        margin: 0;
    }
    .deal-banner p {
        color: #b0bec5;
        font-size: 0.95rem;
        margin-top: 0.5rem;
    }

    /* Score display card */
    .score-card {
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        margin: 1.5rem 0;
        transition: all 0.3s ease;
        border: 2px solid rgba(255,255,255,0.1);
    }
    .score-card .score-number {
        font-size: 4rem;
        font-weight: 800;
        color: #ffffff;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        line-height: 1;
    }
    .score-card .score-label {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.7);
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 0.3rem;
    }
    .score-card .score-descriptor {
        font-size: 1.15rem;
        color: #ffffff;
        font-style: italic;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.2);
    }

    /* Success message */
    .success-box {
        background: linear-gradient(135deg, #1b5e20, #2e7d32);
        border: 1px solid #43a047;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
    }
    .success-box h3 {
        color: #ffffff;
        margin: 0 0 0.5rem 0;
    }
    .success-box p {
        color: #c8e6c9;
        margin: 0;
    }

    /* Results table */
    .results-table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
    }
    .results-table th {
        background: #1a237e;
        color: #ffffff;
        padding: 12px 16px;
        text-align: left;
        font-weight: 600;
    }
    .results-table td {
        padding: 10px 16px;
        border-bottom: 1px solid #2d2d5e;
        color: #e0e0e0;
    }
    .results-table tr:hover {
        background: rgba(255,255,255,0.05);
    }

    /* Stats cards */
    .stat-card {
        background: linear-gradient(135deg, #1a1a3e, #2d2d5e);
        border: 1px solid #3949ab;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .stat-card .stat-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #7c8dff;
    }
    .stat-card .stat-label {
        font-size: 0.8rem;
        color: #8888aa;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* No active deal */
    .no-deal-box {
        background: linear-gradient(135deg, #1a1a3e, #2d2d5e);
        border: 1px solid #3949ab;
        border-radius: 12px;
        padding: 3rem;
        text-align: center;
        margin: 2rem 0;
    }
    .no-deal-box h3 {
        color: #e0e0e0;
    }
    .no-deal-box p {
        color: #8888aa;
    }

    /* Form styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #1a1a3e !important;
        border: 1px solid #3949ab !important;
        color: #e0e0e0 !important;
    }

    /* Slider styling */
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #d32f2f, #f9a825, #1b5e20) !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Score reference table */
    .score-ref {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 6px;
        margin: 1rem 0;
    }
    .score-ref-item {
        border-radius: 8px;
        padding: 8px 4px;
        text-align: center;
        font-size: 0.7rem;
        color: #ffffff;
        opacity: 0.7;
        transition: opacity 0.2s;
    }
    .score-ref-item:hover {
        opacity: 1;
    }
    .score-ref-item .ref-num {
        font-size: 1.2rem;
        font-weight: 700;
    }
</style>
""",
    unsafe_allow_html=True,
)


# =============================================
# DATABASE
# =============================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ic_votes.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deal_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        score INTEGER NOT NULL,
        submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (deal_id) REFERENCES deals(id)
    )"""
    )
    conn.commit()
    conn.close()


def get_active_deal():
    conn = get_db()
    deal = conn.execute("SELECT * FROM deals WHERE active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if deal:
        return dict(deal)
    return None


def create_deal(name, description):
    conn = get_db()
    # Deactivate all current deals
    conn.execute("UPDATE deals SET active = 0")
    conn.execute(
        "INSERT INTO deals (name, description) VALUES (?, ?)",
        (name, description),
    )
    conn.commit()
    conn.close()


def submit_vote(deal_id, email, score):
    conn = get_db()
    # Check for existing vote
    existing = conn.execute(
        "SELECT id FROM votes WHERE deal_id = ? AND LOWER(email) = LOWER(?)",
        (deal_id, email),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE votes SET score = ?, submitted_at = ? WHERE id = ?",
            (score, datetime.now().isoformat(), existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO votes (deal_id, email, score, submitted_at) VALUES (?, ?, ?, ?)",
            (deal_id, email, score, datetime.now().isoformat()),
        )
    conn.commit()
    conn.close()
    return existing is not None  # True if updated


def get_votes(deal_id):
    conn = get_db()
    votes = conn.execute(
        "SELECT * FROM votes WHERE deal_id = ? ORDER BY score ASC",
        (deal_id,),
    ).fetchall()
    conn.close()
    return [dict(v) for v in votes]


def delete_votes(deal_id):
    conn = get_db()
    conn.execute("DELETE FROM votes WHERE deal_id = ?", (deal_id,))
    conn.commit()
    conn.close()


def delete_deal(deal_id):
    conn = get_db()
    conn.execute("DELETE FROM votes WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
    conn.commit()
    conn.close()


def get_all_deals():
    conn = get_db()
    deals = conn.execute("SELECT * FROM deals ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(d) for d in deals]


def activate_deal(deal_id):
    conn = get_db()
    conn.execute("UPDATE deals SET active = 0")
    conn.execute("UPDATE deals SET active = 1 WHERE id = ?", (deal_id,))
    conn.commit()
    conn.close()


# =============================================
# EMAIL / REPORT GENERATION
# =============================================
def generate_email_html(deal_name, votes_df, avg_score, median_score):
    rows_html = ""
    for i, row in votes_df.iterrows():
        score = int(row["Score"])
        color = SCORE_COLORS[score]
        rows_html += f"""
        <tr>
            <td style="padding:10px 16px; border-bottom:1px solid #e0e0e0; color:#333;">{i+1}</td>
            <td style="padding:10px 16px; border-bottom:1px solid #e0e0e0; color:#333;">{row['Email']}</td>
            <td style="padding:10px 16px; border-bottom:1px solid #e0e0e0; text-align:center;">
                <span style="background:{color}; color:#fff; padding:4px 12px; border-radius:20px; font-weight:700;">{score}</span>
            </td>
            <td style="padding:10px 16px; border-bottom:1px solid #e0e0e0; color:#666; font-style:italic;">{row['Descriptor']}</td>
        </tr>"""

    html = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background:#f5f5f5; padding:20px;">
        <div style="max-width:800px; margin:0 auto; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.1);">

            <div style="background:linear-gradient(90deg, #1a237e, #283593); padding:24px 32px;">
                <h1 style="color:#ffffff; margin:0; font-size:24px;">IC Conviction Vote Results</h1>
                <p style="color:#b0bec5; margin:8px 0 0 0; font-size:14px;">Deal: {deal_name}</p>
            </div>

            <div style="padding:24px 32px;">
                <div style="display:flex; gap:16px; margin-bottom:24px;">
                    <div style="flex:1; background:#f5f7ff; border-radius:8px; padding:16px; text-align:center;">
                        <div style="font-size:28px; font-weight:800; color:#1a237e;">{avg_score:.1f}</div>
                        <div style="font-size:12px; color:#666; text-transform:uppercase; letter-spacing:1px;">Average</div>
                    </div>
                    <div style="flex:1; background:#f5f7ff; border-radius:8px; padding:16px; text-align:center;">
                        <div style="font-size:28px; font-weight:800; color:#1a237e;">{median_score:.1f}</div>
                        <div style="font-size:12px; color:#666; text-transform:uppercase; letter-spacing:1px;">Median</div>
                    </div>
                    <div style="flex:1; background:#f5f7ff; border-radius:8px; padding:16px; text-align:center;">
                        <div style="font-size:28px; font-weight:800; color:#1a237e;">{len(votes_df)}</div>
                        <div style="font-size:12px; color:#666; text-transform:uppercase; letter-spacing:1px;">Votes</div>
                    </div>
                </div>

                <h3 style="color:#1a237e; margin-bottom:8px;">Votes (Sorted Low to High)</h3>
                <p style="color:#888; font-size:13px; margin-bottom:16px;">Questioning order: lowest scores lead the discussion first.</p>

                <table style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background:#1a237e;">
                            <th style="padding:12px 16px; color:#fff; text-align:left; font-weight:600;">#</th>
                            <th style="padding:12px 16px; color:#fff; text-align:left; font-weight:600;">Email</th>
                            <th style="padding:12px 16px; color:#fff; text-align:center; font-weight:600;">Score</th>
                            <th style="padding:12px 16px; color:#fff; text-align:left; font-weight:600;">Conviction Level</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <div style="margin-top:24px; padding:16px; background:#fff3e0; border-radius:8px; border-left:4px solid #ff9800;">
                    <strong style="color:#e65100;">Discussion Protocol:</strong>
                    <span style="color:#666;"> Members are ordered from lowest to highest conviction. Lower scores lead the questioning to surface key risks and concerns before hearing from advocates.</span>
                </div>
            </div>

            <div style="background:#f5f5f5; padding:16px 32px; text-align:center; font-size:12px; color:#999;">
                Generated by IC Conviction Vote Tool &bull; {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_email_smtp(deal_name, votes_df, avg_score, median_score, smtp_config):
    """Send email via SMTP. smtp_config = dict with host, port, username, password, sender."""
    html_body = generate_email_html(deal_name, votes_df, avg_score, median_score)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"IC Conviction Vote Results: {deal_name}"
    msg["From"] = smtp_config["sender"]
    msg["To"] = RECIPIENT_EMAIL

    # Plain text fallback
    plain_text = f"IC Conviction Vote Results: {deal_name}\n\n"
    plain_text += f"Average: {avg_score:.1f} | Median: {median_score:.1f} | Votes: {len(votes_df)}\n\n"
    plain_text += "Votes (Low to High):\n"
    for i, row in votes_df.iterrows():
        plain_text += f"  {i+1}. {row['Email']} - Score: {row['Score']}\n"

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.starttls()
        server.login(smtp_config["username"], smtp_config["password"])
        server.sendmail(smtp_config["sender"], RECIPIENT_EMAIL, msg.as_string())


def build_votes_dataframe(votes):
    if not votes:
        return pd.DataFrame(columns=["Email", "Score", "Descriptor", "Submitted"])
    data = []
    for v in votes:
        data.append(
            {
                "Email": v["email"],
                "Score": v["score"],
                "Descriptor": DESCRIPTORS[v["score"]],
                "Submitted": v["submitted_at"][:16].replace("T", " "),
            }
        )
    df = pd.DataFrame(data)
    df = df.sort_values("Score", ascending=True).reset_index(drop=True)
    return df


# =============================================
# UI COMPONENTS
# =============================================
def render_score_card(score):
    color = SCORE_COLORS[score]
    descriptor = DESCRIPTORS[score]
    st.markdown(
        f"""
        <div class="score-card" style="background: linear-gradient(135deg, {color}dd, {color}99);">
            <div class="score-number">{score}</div>
            <div class="score-label">out of 10</div>
            <div class="score-descriptor">"{descriptor}"</div>
        </div>
    """,
        unsafe_allow_html=True,
    )


def render_score_reference():
    html = '<div class="score-ref">'
    for i in range(1, 11):
        html += f'<div class="score-ref-item" style="background:{SCORE_COLORS[i]}"><div class="ref-num">{i}</div>{DESCRIPTORS[i][:25]}...</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# =============================================
# MAIN APP
# =============================================
def render_admin_panel():
    """Admin panel rendered in the main page body."""
    deal = get_active_deal()

    st.markdown("---")
    st.markdown("#### Manage Deals")

    col_deal, col_desc = st.columns([1, 1])
    with col_deal:
        deal_name = st.text_input("Deal Name", key="new_deal_name")
    with col_desc:
        deal_desc = st.text_input("Description (optional)", key="new_deal_desc")

    if st.button("Create / Activate Deal", key="create_deal", type="primary"):
        if deal_name.strip():
            create_deal(deal_name.strip(), deal_desc.strip())
            st.success(f"Deal '{deal_name}' is now active!")
            st.rerun()
        else:
            st.error("Enter a deal name")

    # List all deals with delete option
    all_deals = get_all_deals()
    if all_deals:
        st.markdown("---")
        st.markdown("#### Existing Deals")
        for d in all_deals:
            is_active = d["active"] == 1
            label = f"{'[ACTIVE] ' if is_active else ''}{d['name']}"
            if is_active:
                col_label, col_clear, col_del = st.columns([3, 1, 1])
            else:
                col_label, col_activate, col_clear, col_del = st.columns([2.5, 1, 1, 1])
            with col_label:
                color = "#4caf50" if is_active else "#8888aa"
                st.markdown(
                    f'<span style="color:{color}; font-weight:{"700" if is_active else "400"}; line-height:2.4;">{label}</span>',
                    unsafe_allow_html=True,
                )
            if not is_active:
                with col_activate:
                    if st.button("Activate", key=f"activate_{d['id']}", type="primary"):
                        activate_deal(d["id"])
                        st.success(f"'{d['name']}' is now active!")
                        st.rerun()
            with col_clear:
                if st.button("Clear Votes", key=f"clear_{d['id']}"):
                    delete_votes(d["id"])
                    st.success(f"Votes cleared for {d['name']}")
                    st.rerun()
            with col_del:
                if st.button("Delete", key=f"del_{d['id']}"):
                    delete_deal(d["id"])
                    st.success(f"Deleted {d['name']}")
                    st.rerun()


def main():
    init_db()

    # Initialize session state
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    if "vote_submitted" not in st.session_state:
        st.session_state.vote_submitted = False
    if "page" not in st.session_state:
        st.session_state.page = "vote"

    deal = get_active_deal()

    # Header
    st.markdown(
        """
        <div class="main-header">
            <h1>IC Conviction Vote</h1>
            <p>TacOpps Committee Voting Tool</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Navigation — always visible in the main body
    if st.session_state.admin_logged_in:
        nav_cols = st.columns([1, 1, 1, 1, 0.6])
        pages = [
            ("vote", "Vote"),
            ("results", "Results Dashboard"),
            ("email", "Send Report"),
            ("admin", "Manage Deals"),
        ]
        for idx, (key, label) in enumerate(pages):
            with nav_cols[idx]:
                btn_type = "primary" if st.session_state.page == key else "secondary"
                if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                    st.session_state.page = key
                    st.rerun()
        with nav_cols[4]:
            if st.button("Logout", key="logout_btn", use_container_width=True):
                st.session_state.admin_logged_in = False
                st.session_state.page = "vote"
                st.rerun()

        st.markdown("")

        # Render selected page
        if st.session_state.page == "vote":
            if deal:
                render_voting_form(deal)
            else:
                st.warning("No active deal. Go to **Manage Deals** to create one.")
        elif st.session_state.page == "results":
            if deal:
                render_results_dashboard(deal)
            else:
                st.warning("No active deal yet.")
        elif st.session_state.page == "email":
            if deal:
                render_email_panel(deal)
            else:
                st.warning("No active deal yet.")
        elif st.session_state.page == "admin":
            render_admin_panel()

    else:
        # Non-admin view: voting form + admin login at bottom
        if deal:
            render_voting_form(deal)
        else:
            st.markdown(
                """
                <div class="no-deal-box">
                    <h3>No Active Deal</h3>
                    <p>An admin needs to create a deal before voting can begin.<br>
                    Ask your deal lead to set up the vote.</p>
                </div>
            """,
                unsafe_allow_html=True,
            )

        # Admin login at the bottom of the page
        st.markdown("")
        st.markdown("")
        with st.expander("Admin Access"):
            pwd = st.text_input("Password", type="password", key="admin_pwd")
            if st.button("Login", key="admin_login"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.session_state.page = "admin"
                    st.rerun()
                else:
                    st.error("Incorrect password")


def render_voting_form(deal):
    # Deal banner
    desc_html = f"<p>{deal['description']}</p>" if deal.get("description") else ""
    st.markdown(
        f"""
        <div class="deal-banner">
            <h2>{deal['name']}</h2>
            {desc_html}
        </div>
    """,
        unsafe_allow_html=True,
    )

    if st.session_state.vote_submitted:
        st.markdown(
            """
            <div class="success-box">
                <h3>Vote Submitted!</h3>
                <p>Your conviction has been recorded. May the IRR be ever in your favor.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("Submit Another Vote"):
            st.session_state.vote_submitted = False
            st.rerun()
        return

    # Voting Form
    email = st.text_input("Email Address", placeholder="first.last@blackstone.com", key="email")

    st.markdown("#### Your Conviction Score")

    score = st.slider(
        "Slide to select your conviction level",
        min_value=1,
        max_value=10,
        value=5,
        key="score_slider",
    )

    render_score_card(score)

    st.markdown("")  # spacer

    if st.button("Submit Vote", type="primary", use_container_width=True):
        if not email.strip() or "@" not in email:
            st.error("Please enter a valid email address.")
        else:
            was_update = submit_vote(
                deal["id"],
                email.strip(),
                score,
            )
            st.session_state.vote_submitted = True
            st.rerun()

    # Score reference
    with st.expander("Full Conviction Scale Reference"):
        for s in range(1, 11):
            color = SCORE_COLORS[s]
            st.markdown(
                f'<span style="background:{color}; color:#fff; padding:2px 10px; border-radius:12px; font-weight:700; margin-right:8px;">{s}</span> {DESCRIPTORS[s]}',
                unsafe_allow_html=True,
            )


def render_results_dashboard(deal):
    votes = get_votes(deal["id"])

    if not votes:
        st.info("No votes yet. Share the link with IC members to start collecting votes.")
        return

    df = build_votes_dataframe(votes)
    scores = df["Score"].tolist()
    avg_score = statistics.mean(scores)
    median_score = statistics.median(scores)

    # Stats row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-value">{avg_score:.1f}</div>
                <div class="stat-label">Average</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-value">{median_score:.1f}</div>
                <div class="stat-label">Median</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-value">{len(votes)}</div>
                <div class="stat-label">Total Votes</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.markdown("#### Votes — Sorted Low to High (Discussion Order)")
    st.markdown(
        "*Lowest conviction leads questioning first to surface risks before advocates speak.*"
    )

    # Styled results table
    table_html = """<table class="results-table">
        <thead><tr>
            <th>#</th><th>Email</th><th>Score</th><th>Conviction Level</th>
        </tr></thead><tbody>"""

    for i, row in df.iterrows():
        score = int(row["Score"])
        color = SCORE_COLORS[score]
        table_html += f"""<tr>
            <td>{i+1}</td>
            <td><strong>{row['Email']}</strong></td>
            <td><span style="background:{color}; color:#fff; padding:3px 10px; border-radius:16px; font-weight:700;">{score}</span></td>
            <td style="font-style:italic; color:#8888aa;">{row['Descriptor']}</td>
        </tr>"""

    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)


def render_email_panel(deal):
    votes = get_votes(deal["id"])

    if not votes:
        st.info("No votes to report yet.")
        return

    df = build_votes_dataframe(votes)
    scores = df["Score"].tolist()
    avg_score = statistics.mean(scores)
    median_score = statistics.median(scores)

    st.markdown("#### Send Results to Your Email")
    st.markdown(f"Results will be sent to **{RECIPIENT_EMAIL}**")

    # Option 1: Download HTML report
    st.markdown("---")
    st.markdown("##### Option 1: Download HTML Report")
    st.markdown("Download a formatted report you can open in any browser or forward via email.")

    html_report = generate_email_html(deal["name"], df, avg_score, median_score)
    st.download_button(
        label="Download HTML Report",
        data=html_report,
        file_name=f"IC_Vote_{deal['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html",
        mime="text/html",
        use_container_width=True,
    )

    # Option 2: Copy plain text
    st.markdown("---")
    st.markdown("##### Option 2: Copy Plain Text Summary")

    plain = f"IC CONVICTION VOTE RESULTS\n"
    plain += f"Deal: {deal['name']}\n"
    plain += f"Date: {datetime.now().strftime('%B %d, %Y')}\n"
    plain += f"{'='*50}\n\n"
    plain += f"SUMMARY STATS\n"
    plain += f"  Average Score:  {avg_score:.1f} / 10\n"
    plain += f"  Median Score:   {median_score:.1f} / 10\n"
    plain += f"  Total Votes:    {len(votes)}\n\n"
    plain += f"VOTES (Sorted Low to High — Discussion Order)\n"
    plain += f"{'-'*50}\n"
    for i, row in df.iterrows():
        plain += f"\n  {i+1}. {row['Email']}\n"
        plain += f"     Score: {row['Score']}/10 — \"{row['Descriptor']}\"\n"
    plain += f"\n{'='*50}\n"
    plain += f"Lowest scores lead questioning to surface risks first.\n"

    st.code(plain, language=None)

    # Option 3: SMTP
    st.markdown("---")
    st.markdown("##### Option 3: Send via SMTP")
    st.markdown("Configure SMTP to send directly from the app.")

    with st.expander("SMTP Configuration"):
        smtp_host = st.text_input("SMTP Host", value="smtp.gmail.com", key="smtp_host")
        smtp_port = st.number_input("SMTP Port", value=587, key="smtp_port")
        smtp_user = st.text_input("SMTP Username / Email", key="smtp_user")
        smtp_pass = st.text_input("SMTP Password / App Password", type="password", key="smtp_pass")
        smtp_sender = st.text_input("Sender Email", value=smtp_user if smtp_user else "", key="smtp_sender")

        if st.button("Send Email Now", key="send_smtp"):
            if not smtp_user or not smtp_pass:
                st.error("Please fill in SMTP credentials.")
            else:
                try:
                    send_email_smtp(
                        deal["name"],
                        df,
                        avg_score,
                        median_score,
                        {
                            "host": smtp_host,
                            "port": int(smtp_port),
                            "username": smtp_user,
                            "password": smtp_pass,
                            "sender": smtp_sender or smtp_user,
                        },
                    )
                    st.success(f"Email sent to {RECIPIENT_EMAIL}!")
                except Exception as e:
                    st.error(f"Failed to send email: {str(e)}")


if __name__ == "__main__":
    main()

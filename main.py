import streamlit as st
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Health check server runs on port 8080 (Streamlit Cloud checks this port)
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logging

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    server.serve_forever()

# Start health server in background thread
health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()

# Now run Streamlit
from data_loader import DataLoader, convert_name_to_ticker
from scorers import ScoringEngine
from utils import get_rating

st.set_page_config(page_title="Thesis Prototype", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@200;400;700;800&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── Base — AUREUM SLATE dark surface ── */
    .stApp {
        background-color: #111316 !important;
        background-image:
            repeating-linear-gradient(90deg, transparent, transparent 39px, rgba(242,202,80,0.02) 39px, rgba(242,202,80,0.02) 40px),
            repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(242,202,80,0.02) 39px, rgba(242,202,80,0.02) 40px);
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* ── Header ── */
    .main-header {
        font-family: 'Manrope', sans-serif;
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        letter-spacing: -0.03em;
        color: #f2ca50;
        margin-bottom: 8px;
        font-style: normal;
    }
    .sub-header {
        text-align: center;
        color: #c6c6c6;
        margin-bottom: 32px;
        font-style: italic;
        font-weight: 300;
        letter-spacing: 0.08em;
        font-size: 0.95rem;
    }

    /* ── Input ── */
    .stTextInput > div > div > input {
        background-color: #1a1c1f !important;
        color: #e2e2e6 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 0.125rem !important;
        padding: 14px 12px !important;
        font-family: 'Manrope', sans-serif !important;
        outline: none !important;
        box-shadow: none !important;
        transition: all 0.2s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #f2ca50 !important;
        box-shadow: 0 0 0 2px rgba(242,202,80,0.15) !important;
    }
    .stTextInput > div > div > input::placeholder { color: #6b6d70 !important; opacity: 0.7 !important; }

    /* ── Button — clean minimal ── */
    div.stButton > button,
    div.stButton > button:focus,
    div.stButton > button:active {
        width: 100% !important;
        background: linear-gradient(135deg, #f2ca50 0%, #d4af37 100%) !important;
        color: #111316 !important;
        font-weight: 800 !important;
        font-family: 'Manrope', sans-serif !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        border: none !important;
        border-radius: 0.25rem !important;
        padding: 16px 12px !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3) !important;
        transition: all 0.2s !important;
    }
    div.stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 12px 32px rgba(242,202,80,0.25) !important;
    }

    /* ── Metric cards ── */
    .metric-card {
        background: linear-gradient(180deg, rgba(26,28,31,0.8) 0%, rgba(17,19,22,0.9) 100%);
        backdrop-filter: blur(20px);
        border-radius: 0.5rem;
        padding: 32px 24px;
        text-align: center;
        border: 1px solid rgba(242,202,80,0.2);
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }
    .metric-value {
        font-size: 36px;
        font-weight: 900;
        color: #e2e2e6;
        margin-top: 8px;
        font-family: 'Manrope', sans-serif;
        letter-spacing: -0.02em;
    }
    .metric-title {
        font-size: 10px;
        color: #c6c6c6;
        text-transform: uppercase;
        letter-spacing: 0.25em;
        font-weight: 600;
    }

    /* ── Sentiment boxes ── */
    .sent-box {
        background: rgba(26,28,31,0.6);
        backdrop-filter: blur(10px);
        border-radius: 0.5rem;
        padding: 14px;
        text-align: center;
        margin-bottom: 12px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .sent-val { font-size: 22px; font-weight: 900; font-family: 'Manrope', sans-serif; letter-spacing: -0.01em; }
    .sent-label { font-size: 9px; color: #c6c6c6; text-transform: uppercase; letter-spacing: 0.16em; font-weight: 600; margin-top: 4px; }

    /* ── Links ── */
    a { color: #f2ca50 !important; text-decoration: none; font-weight: 600; }
    a:hover { text-decoration: underline; opacity: 0.9; }
    .news-link { font-size: 0.82em; font-weight: 700; margin-top: 8px; display: block; }

    /* ── Data labels ── */
    .data-label { color: #c6c6c6; font-size: 10px; text-transform: uppercase; letter-spacing: 0.18em; font-weight: 700; }
    .data-val { color: #e2e2e6; font-size: 1.1em; font-weight: 700; margin-bottom: 14px; letter-spacing: -0.01em; }
    .ext-link { font-size: 0.8em; margin-top: 12px; display: block; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px; }

    /* ── Signal pills ── */
    .fsig-pass { display:inline-block; background:rgba(242,202,80,0.15); border:1px solid #f2ca50; color:#f2ca50; border-radius:0.25rem; padding:4px 10px; font-size:0.75em; margin:3px; font-weight: 700; }
    .fsig-fail { display:inline-block; background:rgba(255,180,171,0.15); border:1px solid #ffb4ab; color:#ffb4ab; border-radius:0.25rem; padding:4px 10px; font-size:0.75em; margin:3px; font-weight: 700; }

    /* ── Pillar bars ── */
    .pillar-row { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05); }
    .pillar-name { font-size:0.78em; color:#c6c6c6; text-transform:uppercase; letter-spacing:0.14em; font-weight:700; }
    .pillar-bar-bg { flex:1; margin:0 12px; height:3px; background:#1e2023; border-radius:0; }
    .pillar-bar-fill { height:3px; border-radius:0; }
    .pillar-val { font-size:0.9em; font-weight:900; min-width:32px; text-align:right; }

    /* ── Progress bars ── */
    .stProgress > div > div > div > div { background: linear-gradient(90deg, #f2ca50 0%, #d4af37 100%) !important; }
    .stProgress > div > div { background-color: #1e2023 !important; border-radius: 0.25rem !important; height: 4px !important; }

    /* ── Dividers ── */
    hr { border-color: rgba(255,255,255,0.1) !important; }

    /* ── Expanders ── */
    div[data-testid="stExpander"] { background: rgba(26,28,31,0.6) !important; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 0.5rem; box-shadow: 0 2px 12px rgba(0,0,0,0.3); }
    div[data-testid="stExpander"] details summary p { color: #f2ca50 !important; font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 800; }

    /* ── Streamlit containers ── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(180deg, rgba(26,28,31,0.7) 0%, rgba(17,19,22,0.8) 100%) !important;
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 0.5rem;
        padding: 4px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    }

    /* ── Headings ── */
    h3 { font-family: 'Manrope', sans-serif !important; font-weight: 800 !important; color: #e2e2e6 !important; letter-spacing: -0.01em !important; }
    h2 { font-family: 'Manrope', sans-serif !important; color: #e2e2e6 !important; font-weight: 800 !important; }

    /* ── Info/Error/Warning boxes ── */
    .stAlert {
        background: rgba(26,28,31,0.8) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 0.5rem !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">AI STOCK EVALUATION</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Refining market noise into institutional-grade clarity.</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    with st.form(key='search_form'):
        user_input = st.text_input("", placeholder="Enter Ticker or Company Name (e.g. Nvidia, AAPL)...")
        submit_button = st.form_submit_button(label='EXECUTE ANALYSIS')

if submit_button and user_input:
    ticker = convert_name_to_ticker(user_input)
    loader = DataLoader()
    engine = ScoringEngine()

    status = st.empty()
    status.info(f"🔄 Finding data for {ticker}...")

    df_tech = loader.get_technical_data(ticker)

    if df_tech is None or df_tech.empty:
        status.empty()
        st.error(f"❌ Could not find data for '{user_input}' (Resolved: {ticker}). Please check the name or ticker.")
    else:
        status.info(f"🔄 Fetching Real-Time Analysis for {ticker}...")

        score_tech, meta_tech   = engine.calculate_technical(df_tech)
        data_social, social_src = loader.get_social_sentiment(ticker)
        data_deriv              = loader.get_derivative_data(ticker)
        data_fund               = loader.get_fundamental_data(ticker)

        score_social, meta_social = engine.calculate_social(data_social)
        score_deriv,  meta_deriv  = engine.calculate_derivative(data_deriv)
        score_fund,   meta_fund   = engine.calculate_fundamental(data_fund)

        # Weights: Fundamentals 40% | Sentiment 25% | Technical 20% | Derivatives 15%
        base_composite = (
            score_fund   * 0.40 +
            score_social * 0.25 +
            score_tech   * 0.20 +
            score_deriv  * 0.15
        )

        insider_buys    = meta_fund.get('insider_buys', 0)
        insider_sells   = meta_fund.get('insider_sells', 0)
        insider_booster = meta_fund.get('insider_booster', 0)
        composite       = min(100, base_composite + insider_booster)

        rating_text, rating_color = get_rating(composite)
        status.empty()

        company_name = meta_fund.get('longName') or meta_fund.get('shortName') or ticker
        sector       = meta_fund.get('sector', '')
        industry     = meta_fund.get('industry', '')

        st.markdown(f"<h3 style='text-align:center;font-family:Manrope,sans-serif;font-weight:800;letter-spacing:-0.01em;color:#e2e2e6;'>{ticker} &nbsp;<span style='color:#c6c6c6;font-weight:400;font-size:0.7em;'>{company_name}</span></h3>", unsafe_allow_html=True)
        if sector or industry:
            st.markdown(f"<p style='text-align:center;color:#c6c6c6;font-size:0.78em;margin-top:-10px;text-transform:uppercase;letter-spacing:0.1em;'>{sector}{' · ' + industry if industry else ''}</p>", unsafe_allow_html=True)

        # ── Competitors strip ──
        competitors = loader.get_competitors(ticker, company_name, sector, industry)
        if competitors:
            chips_html = ''.join([
                f'<a href="?ticker={c["ticker"]}" style="display:inline-block;background:rgba(26,28,31,0.8);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.08);'
                f'border-radius:0.25rem;padding:4px 14px;margin:3px;font-size:0.78em;color:#c6c6c6;text-decoration:none;'
                f'cursor:pointer;transition:all 0.2s;" title="{c.get("name","")}" onmouseover="this.style.borderColor=\'#f2ca50\';this.style.transform=\'translateY(-1px)\'" onmouseout="this.style.borderColor=\'rgba(255,255,255,0.08)\';this.style.transform=\'translateY(0)\'">'
                f'<span style="color:#f2ca50;font-weight:700;font-family:Manrope,sans-serif;">{c["ticker"]}</span>'
                f'&nbsp;<span style="color:#c6c6c6;">{c.get("name","")}</span></a>'
                for c in competitors
            ])
            st.markdown(
                f'<div style="text-align:center;margin:4px 0 12px 0;">'
                f'<span style="font-size:0.7em;color:#c6c6c6;text-transform:uppercase;letter-spacing:0.15em;margin-right:8px;">Peers</span>'
                f'{chips_html}</div>',
                unsafe_allow_html=True
            )
        st.markdown("---")

        # ── Top metrics ──
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""<div class="metric-card" style="border-top:3px solid {rating_color};">
                <div class="metric-title">Composite Score</div>
                <div class="metric-value" style="color:{rating_color};font-size:2.2rem;">{composite:.1f}<span style="font-size:0.45em;color:#a89060;">/100</span></div>
            </div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="metric-card" style="border-top:3px solid {rating_color};">
                <div class="metric-title">Signal Strength</div>
                <div class="metric-value" style="color:{rating_color};font-size:1.35rem;margin-top:10px;">{rating_text}</div>
            </div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class="metric-card" style="border-top:3px solid rgba(0,0,0,0.1);">
                <div class="metric-title">Current Price</div>
                <div class="metric-value" style="font-size:2rem;">${df_tech['Close'].iloc[-1]:.2f}</div>
            </div>""", unsafe_allow_html=True)

        # ── Insider banner ──
        if insider_buys > 10:
            emoji, title, color = "▲", f"MASSIVE INSIDER CLUSTER BUYING (+{insider_booster:.1f} pts)", "#f2ca50"
        elif insider_buys > 0:
            emoji, title, color = "▲", f"INSIDER BUYING DETECTED (+{insider_booster:.1f} pts)", "#d4af37"
        else:
            emoji, title, color = "—", "CORPORATE INSIDER ACTIVITY (+0 pts)", "#a89060"

        st.markdown(f"""
        <div style="background:linear-gradient(90deg,rgba({'242,202,80' if color == '#f2ca50' else '212,175,55' if color == '#d4af37' else '168,144,96'},0.15) 0%,rgba(17,19,22,0) 100%);
                    border-left:3px solid {color};padding:16px 18px;border-radius:0.5rem;margin:20px 0;backdrop-filter:blur(10px);">
            <div style="font-family:Manrope,sans-serif;font-size:0.75em;font-weight:800;color:{color};letter-spacing:0.15em;text-transform:uppercase;margin-bottom:6px;">{emoji} {title}</div>
            <div style="color:#e2e2e6;font-size:0.9em;margin-top:4px;">
                <span style="font-size:0.75em;text-transform:uppercase;letter-spacing:0.1em;color:#c6c6c6;">12-Month Transactions · </span>
                <span style="color:#f2ca50;font-weight:700;">{insider_buys} Buys</span>
                <span style="color:#c6c6c6;"> · </span>
                <span style="color:#ffb4ab;font-weight:700;">{insider_sells} Sells</span>
            </div>
            <div style="margin-top:10px;font-size:0.82em;color:#c6c6c6;font-style:italic;">Insiders only buy when they expect the price to rise.</div>
            <div style="margin-top:10px;font-size:0.82em;">
                <a href="http://openinsider.com/search?q={ticker}" target="_blank" style="color:#f2ca50;font-weight:600;">OpenInsider Log ↗</a>
                &nbsp;&nbsp;·&nbsp;&nbsp;
                <a href="https://finance.yahoo.com/quote/{ticker}/insider-transactions" target="_blank" style="color:#f2ca50;font-weight:600;">Yahoo Finance ↗</a>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='font-family:Manrope,sans-serif;font-size:0.72em;font-weight:800;color:#c6c6c6;text-transform:uppercase;letter-spacing:0.2em;margin:20px 0 10px 0;'>Signal Breakdown</div>", unsafe_allow_html=True)
        c_left, c_right = st.columns([1, 1.5])

        with c_left:
            # ── Fundamentals ──
            with st.container(border=True):
                dist_tag = " — DISTRESSED ASSET" if meta_fund.get('is_distressed') else ""
                p_raw    = meta_fund.get('piotroski_raw', 0)
                p_max    = meta_fund.get('piotroski_max', 0)
                f_badge  = f" · F-Score {p_raw}/{p_max}" if p_max > 0 else ""
                st.markdown(f"<div style='font-family:Manrope,sans-serif;font-size:0.7em;font-weight:800;color:#f2ca50;text-transform:uppercase;letter-spacing:0.18em;margin-bottom:4px;'>Fundamentals<span style='color:#c6c6c6;font-weight:400;'> · {score_fund:.0f}{f_badge}{dist_tag}</span></div>", unsafe_allow_html=True)
                st.progress(int(score_fund))

                # 5-pillar mini breakdown
                pillar_scores = meta_fund.get('pillar_scores', {})
                pillar_colors = {
                    'Profitability': '#f2ca50',
                    'Growth':        '#bfcdff',
                    'Valuation':     '#d4af37',
                    'Health':        '#bfcdff',
                    'FCF Quality':   '#e9c349',
                }
                if pillar_scores:
                    rows_html = ""
                    for pname, pval in pillar_scores.items():
                        if pval is None:
                            continue
                        pcolor = pillar_colors.get(pname, '#c6c6c6')
                        bar_width = max(2, pval)
                        rows_html += (
                            f'<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                            f'<span style="font-size:0.78em;color:#c6c6c6;text-transform:uppercase;letter-spacing:0.1em;min-width:90px;">{pname}</span>'
                            f'<div style="flex:1;margin:0 12px;height:4px;background:#1e2023;border-radius:2px;">'
                            f'<div style="width:{bar_width}%;height:4px;border-radius:2px;background:{pcolor};"></div>'
                            f'</div>'
                            f'<span style="font-size:0.88em;font-weight:700;color:{pcolor};min-width:32px;text-align:right;">{pval}</span>'
                            f'</div>'
                        )
                    st.markdown(f'<div style="background:rgba(26,28,31,0.6);backdrop-filter:blur(10px);border-radius:0.5rem;padding:12px 16px;margin:8px 0;border:1px solid rgba(255,255,255,0.08);"><div style="font-size:0.68em;color:#c6c6c6;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:8px;">Factor Breakdown</div>{rows_html}</div>', unsafe_allow_html=True)

                def fmt_fp(v):  return f"{v*100:.1f}%" if v is not None else "N/A"
                def fmt_fn(v):  return f"{v:.2f}"      if v is not None else "N/A"
                def fmt_de(v):  return f"{v/100:.2f}"  if v is not None else "N/A"

                pe_med = meta_fund.get('sector_pe_median')

                fc1, fc2 = st.columns(2)
                with fc1:
                    pe_label = f"P/E Ratio (vs ~{pe_med}x sector)" if pe_med else "P/E Ratio"
                    st.markdown(f"<div class='data-label'>{pe_label}</div><div class='data-val'>{fmt_fn(meta_fund.get('PE'))}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-label'>Return on Equity</div><div class='data-val'>{fmt_fp(meta_fund.get('ROE'))}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-label'>Revenue Growth</div><div class='data-val'>{fmt_fp(meta_fund.get('RevGrowth'))}</div>", unsafe_allow_html=True)
                with fc2:
                    st.markdown(f"<div class='data-label'>P/B Ratio</div><div class='data-val'>{fmt_fn(meta_fund.get('PB'))}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-label'>Net Margin</div><div class='data-val'>{fmt_fp(meta_fund.get('Margins'))}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-label'>Debt-to-Equity</div><div class='data-val'>{fmt_de(meta_fund.get('DebtEq'))}</div>", unsafe_allow_html=True)

                # Piotroski signal pills (secondary detail)
                p_sigs = meta_fund.get('piotroski_signals', {})
                if p_sigs:
                    with st.expander("Piotroski F-Score Signals"):
                        pills = ""
                        for lbl, val in p_sigs.items():
                            css  = "fsig-pass" if val == 1 else "fsig-fail"
                            icon = "✓" if val == 1 else "✗"
                            pills += f'<span class="{css}">{icon} {lbl}</span>'
                        st.markdown(f"<div style='margin-top:4px;'>{pills}</div>", unsafe_allow_html=True)

                st.markdown(f"""<div class="ext-link"><a href="https://finance.yahoo.com/quote/{ticker}/financials" target="_blank">View Financial Statements ↗</a></div>""", unsafe_allow_html=True)

            # ── Sentiment ──
            with st.container(border=True):
                st.markdown(f"<div style='font-family:Manrope,sans-serif;font-size:0.7em;font-weight:800;color:#f2ca50;text-transform:uppercase;letter-spacing:0.18em;margin-bottom:4px;'>AI Sentiment<span style='color:#c6c6c6;font-weight:400;'> · {score_social:.0f}</span></div>", unsafe_allow_html=True)
                st.progress(int(score_social))
                st.markdown(f"<div style='color:#c6c6c6;font-size:0.82em;font-style:italic;margin:4px 0 10px 0;'>{meta_social['summary']}</div>", unsafe_allow_html=True)

                counts = meta_social.get('counts', {'bull': 0, 'bear': 0, 'neut': 0})
                b1, b2, b3 = st.columns(3)
                b1.markdown(f"""<div class="sent-box"><div class="sent-val" style="color:#f2ca50">{counts['bull']}</div><div class="sent-label">Bullish</div></div>""", unsafe_allow_html=True)
                b2.markdown(f"""<div class="sent-box"><div class="sent-val" style="color:#c6c6c6">{counts['neut']}</div><div class="sent-label">Neutral</div></div>""", unsafe_allow_html=True)
                b3.markdown(f"""<div class="sent-box"><div class="sent-val" style="color:#ffb4ab">{counts['bear']}</div><div class="sent-label">Bearish</div></div>""", unsafe_allow_html=True)

                with st.expander("View Analyzed Headlines & Sources"):
                    details = sorted(meta_social.get('details', []), key=lambda x: x.get('score', 0), reverse=True)
                    if not details:
                        st.write("No headlines found.")
                    for item in details:
                        sent = item.get('sentiment', 'Neutral')
                        src  = item.get('source', 'News')
                        if "bullish" in sent.lower(): bc = "#f2ca50"
                        elif "bearish" in sent.lower(): bc = "#ffb4ab"
                        else: bc = "#c6c6c6"
                        st.markdown(f"""
                        <div style="background:rgba(26,28,31,0.6);backdrop-filter:blur(10px);border-left:3px solid {bc};padding:10px 14px;margin-bottom:8px;border-radius:0.25rem;border:1px solid rgba(255,255,255,0.08);">
                            <div style="font-weight:600;font-size:0.9em;color:#e2e2e6;">{item['title']}</div>
                            <div style="font-size:0.75em;color:#c6c6c6;margin-top:5px;display:flex;justify-content:space-between;">
                                <span style="text-transform:uppercase;letter-spacing:0.08em;">{src} · {item['time']}</span>
                                <span style="color:{bc};">Impact {item['score']}/10</span>
                            </div>
                            <div class="news-link"><a href="{item['link']}" target="_blank">Read Article ↗</a></div>
                        </div>""", unsafe_allow_html=True)

            # ── Technical ──
            with st.container(border=True):
                st.markdown(f"<div style='font-family:Manrope,sans-serif;font-size:0.7em;font-weight:800;color:#f2ca50;text-transform:uppercase;letter-spacing:0.18em;margin-bottom:4px;'>Technical Analysis<span style='color:#c6c6c6;font-weight:400;'> · {score_tech:.0f}</span></div>", unsafe_allow_html=True)
                st.progress(int(score_tech))

                price  = meta_tech.get('Price', 0)
                macd_s = "Bullish Cross" if meta_tech.get('MACD', 0) > meta_tech.get('MACD_Signal', 0) else "Bearish Cross"

                ema20  = meta_tech.get('EMA20', 0)
                sma50  = meta_tech.get('SMA50', 0)
                sma200 = meta_tech.get('SMA200', 0)
                if price > ema20 > sma50 > sma200:    trend_s = "Strong Uptrend"
                elif price > sma50 > sma200:           trend_s = "Uptrend"
                elif price < sma50 and price > sma200: trend_s = "Weakening / Pullback"
                elif price < sma200:                   trend_s = "Downtrend"
                else:                                  trend_s = "Mixed/Consolidating"

                bb_hi = meta_tech.get('BB_High', 0)
                bb_lo = meta_tech.get('BB_Low', 0)
                if price > bb_hi:   bb_s = "Upper Band (Breakout)" if meta_tech.get('Trend') else "Overbought"
                elif price < bb_lo: bb_s = "Lower Band (Support)"  if meta_tech.get('Trend') else "Oversold"
                else:               bb_s = "Mid-Channel"

                tc1, tc2 = st.columns(2)
                with tc1:
                    st.markdown(f"<div class='data-label'>RSI (14)</div><div class='data-val'>{meta_tech.get('RSI',0):.1f}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-label'>MACD</div><div class='data-val'>{macd_s}</div>", unsafe_allow_html=True)
                with tc2:
                    st.markdown(f"<div class='data-label'>Trend (vs 200 SMA)</div><div class='data-val'>{trend_s}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-label'>Volatility (BB)</div><div class='data-val'>{bb_s}</div>", unsafe_allow_html=True)

                sig_html = ""
                for lbl, s in meta_tech.get('signal_details', []):
                    css  = "fsig-pass" if s == 1 else "fsig-fail"
                    icon = "✓" if s == 1 else "✗"
                    sig_html += f'<span class="{css}">{icon} {lbl}</span>'
                if sig_html:
                    st.markdown(f"<div style='margin-top:10px;'>{sig_html}</div>", unsafe_allow_html=True)

            # ── Derivatives ──
            with st.container(border=True):
                st.markdown(f"<div style='font-family:Manrope,sans-serif;font-size:0.7em;font-weight:800;color:#f2ca50;text-transform:uppercase;letter-spacing:0.18em;margin-bottom:4px;'>Derivatives & Options<span style='color:#c6c6c6;font-weight:400;'> · {score_deriv:.0f}</span></div>", unsafe_allow_html=True)
                st.progress(int(score_deriv))

                def fmt_num(v): return f"{v:.2f}" if v is not None else "N/A"
                def fmt_pct(v): return f"{v:.1f}%" if v is not None else "N/A"

                pcr_v   = meta_deriv.get('pcr_vol')
                pcr_o   = meta_deriv.get('pcr_oi')
                s_float = meta_deriv.get('short_float')
                s_ratio = meta_deriv.get('short_ratio')
                iv      = meta_deriv.get('avg_iv')

                dc1, dc2 = st.columns(2)
                with dc1:
                    st.markdown(f"<div class='data-label'>Volume P/C Ratio</div><div class='data-val'>{fmt_num(pcr_v)}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-label'>Short Float</div><div class='data-val'>{fmt_pct(s_float)}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-label'>Implied Volatility (IV)</div><div class='data-val'>{fmt_pct(iv)}</div>", unsafe_allow_html=True)
                with dc2:
                    st.markdown(f"<div class='data-label'>Open Interest P/C Ratio</div><div class='data-val'>{fmt_num(pcr_o)}</div>", unsafe_allow_html=True)
                    squeeze = "▲ Squeeze Watch" if (s_ratio and s_float and s_ratio > 8 and s_float > 10 and meta_tech.get('Trend')) else ""
                    st.markdown(f"<div class='data-label'>Days to Cover</div><div class='data-val'>{fmt_num(s_ratio)} <span style='color:#ff8070;font-size:0.8em;'>{squeeze}</span></div>", unsafe_allow_html=True)
                    iv_s = "High Volatility Expected" if iv and iv > 50 else ("Normal Volatility" if iv else "N/A")
                    st.markdown(f"<div class='data-label'>Market Expectation</div><div class='data-val'>{iv_s}</div>", unsafe_allow_html=True)

                st.markdown(f"""<div class="ext-link"><a href="https://finance.yahoo.com/quote/{ticker}/options" target="_blank">View Options Chain ↗</a></div>""", unsafe_allow_html=True)

        # ── Chart ──
        with c_right:
            if not df_tech.empty:
                st.markdown("<div style='font-family:Manrope,sans-serif;font-size:0.7em;font-weight:800;color:#a89060;text-transform:uppercase;letter-spacing:0.2em;margin-bottom:8px;'>Price Action & Indicators</div>", unsafe_allow_html=True)

                from ta.volatility import BollingerBands as BB
                import streamlit.components.v1 as components
                import json

                bb_ind   = BB(df_tech['Close'])
                df_tech['bb_high'] = bb_ind.bollinger_hband()
                df_tech['bb_low']  = bb_ind.bollinger_lband()
                df_tech['sma_50']  = df_tech['Close'].rolling(50).mean()
                df_tech['sma_200'] = df_tech['Close'].rolling(min(200, len(df_tech))).mean()

                # Build data arrays for Lightweight Charts
                def to_ts(idx):
                    return int(idx.timestamp())

                candles = [
                    {"time": to_ts(row.Index), "open": round(float(row.Open), 4),
                     "high": round(float(row.High), 4), "low": round(float(row.Low), 4),
                     "close": round(float(row.Close), 4)}
                    for row in df_tech.itertuples() if not (
                        hasattr(row, 'Open') and str(row.Open) == 'nan'
                    )
                ]

                def line_data(col):
                    return [
                        {"time": to_ts(idx), "value": round(float(v), 4)}
                        for idx, v in df_tech[col].items()
                        if str(v) != 'nan'
                    ]

                sma50_data  = line_data('sma_50')
                sma200_data = line_data('sma_200')
                bb_hi_data  = line_data('bb_high')
                bb_lo_data  = line_data('bb_low')

                candles_json  = json.dumps(candles)
                sma50_json    = json.dumps(sma50_data)
                sma200_json   = json.dumps(sma200_data)
                bb_hi_json    = json.dumps(bb_hi_data)
                bb_lo_json    = json.dumps(bb_lo_data)

                chart_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#111316; }}
  #chart {{ width:100%; height:500px; }}
  #legend {{
    position:absolute; top:8px; left:8px; z-index:10;
    display:flex; gap:14px; flex-wrap:wrap;
    font-family:'Inter',sans-serif; font-size:11px; color:#c6c6c6;
    background:rgba(26,28,31,0.88); padding:5px 12px; border-radius:0.25rem;
    letter-spacing:0.08em; text-transform:uppercase;
    border:1px solid rgba(255,255,255,0.08);
  }}
  .leg {{ display:flex; align-items:center; gap:6px; }}
  .dot {{ width:16px; height:2px; border-radius:1px; }}
</style>
</head>
<body>
<div style="position:relative;">
  <div id="legend">
    <div class="leg"><div class="dot" style="background:#f2ca50;"></div>Price</div>
    <div class="leg"><div class="dot" style="background:#bfcdff;"></div>SMA 50</div>
    <div class="leg"><div class="dot" style="background:#ffb4ab;border-top:2px dashed #ffb4ab;height:0;"></div>SMA 200</div>
    <div class="leg"><div class="dot" style="background:rgba(242,202,80,0.3);"></div>BB Band</div>
  </div>
  <div id="chart"></div>
</div>
<script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
<script>
  const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
    width:  document.getElementById('chart').clientWidth,
    height: 500,
    layout: {{ background: {{ color: '#111316' }}, textColor: '#c6c6c6', fontFamily: 'Inter, sans-serif', fontSize: 11 }},
    grid:   {{ vertLines: {{ color: 'rgba(255,255,255,0.04)' }}, horzLines: {{ color: 'rgba(255,255,255,0.04)' }} }},
    crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
    rightPriceScale: {{ borderColor: 'rgba(255,255,255,0.08)' }},
    timeScale: {{ borderColor: 'rgba(255,255,255,0.08)', timeVisible: true, secondsVisible: false }},
    handleScroll:  {{ mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true }},
    handleScale:   {{ mouseWheel: true, pinch: true, axisPressedMouseMove: true }},
  }});

  // Candlesticks — gold up, red down (AUREUM SLATE palette)
  const cSeries = chart.addCandlestickSeries({{
    upColor: '#f2ca50', downColor: '#ffb4ab',
    borderUpColor: '#d4af37', borderDownColor: '#ffb4ab',
    wickUpColor: '#f2ca50', wickDownColor: '#ffb4ab',
  }});
  cSeries.setData({candles_json});

  // BB upper
  const bbHi = chart.addLineSeries({{ color: 'rgba(242,202,80,0.25)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
  bbHi.setData({bb_hi_json});

  // BB lower
  const bbLo = chart.addLineSeries({{ color: 'rgba(242,202,80,0.25)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
  bbLo.setData({bb_lo_json});

  // SMA 50 — tertiary blue
  const sma50 = chart.addLineSeries({{ color: '#bfcdff', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false }});
  sma50.setData({sma50_json});

  // SMA 200 — error red dashed
  const sma200 = chart.addLineSeries({{ color: '#ffb4ab', lineWidth: 1.5, lineStyle: LightweightCharts.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false }});
  sma200.setData({sma200_json});

  chart.timeScale().fitContent();

  window.addEventListener('resize', () => {{
    chart.applyOptions({{ width: document.getElementById('chart').clientWidth }});
  }});
</script>
</body>
</html>
"""
                components.html(chart_html, height=510, scrolling=False)

                st.markdown(f"""
                <div style="text-align:right;margin-top:6px;font-family:Inter,sans-serif;font-size:0.78em;text-transform:uppercase;letter-spacing:0.1em;">
                    <a href="https://www.tradingview.com/chart/?symbol={ticker}" target="_blank" style="color:#f2ca50;font-weight:600;">View on TradingView ↗</a>
                </div>""", unsafe_allow_html=True)

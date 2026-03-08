import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from groq import Groq
import json
import os
from dotenv import load_dotenv
import streamlit as st
from urllib.parse import urlparse

api_keys_str = None
try:
    if "GROQ_KEYS" in st.secrets:
        api_keys_str = st.secrets["GROQ_KEYS"]
except Exception:
    pass

if not api_keys_str:
    load_dotenv()
    api_keys_str = os.getenv("GROQ_KEYS")

API_KEY_POOL = [k.strip() for k in api_keys_str.split(",") if k.strip()] if api_keys_str else []


def convert_name_to_ticker(user_input):
    clean = user_input.strip()
    if len(clean) <= 5 and clean.isalpha() and clean.isupper():
        return clean

    queries = [clean]
    if " " in clean:
        queries.append(clean.replace(" ", ""))
    if " and " in clean.lower():
        queries.append(clean.lower().replace(" and ", " & "))

    us_exchanges = ['NYQ', 'NMS', 'NGM', 'NCM', 'ASE', 'PCX']
    headers = {'User-Agent': 'Mozilla/5.0'}

    for q in queries:
        try:
            url  = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}"
            data = requests.get(url, headers=headers, timeout=3).json()
            for quote in data.get('quotes', []):
                if quote.get('quoteType') == 'EQUITY' and quote.get('exchange') in us_exchanges:
                    return quote['symbol']
        except Exception:
            continue
    return clean.upper()


class DataLoader:
    def __init__(self):
        pass

    def get_technical_data(self, ticker):
        try:
            df = yf.Ticker(ticker).history(period="1y")
            return df if not df.empty else None
        except Exception:
            return None

    def get_fundamental_data(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            if 'regularMarketPrice' not in info and 'currentPrice' not in info:
                return {}

            # Insider transactions
            insider_buys = insider_sells = 0
            try:
                tx = stock.insider_transactions
                if tx is not None and not tx.empty:
                    for _, row in tx.iterrows():
                        t = str(row.values).lower()
                        if 'purchase' in t or 'buy' in t:
                            insider_buys += 1
                        elif 'sale' in t or 'sell' in t:
                            insider_sells += 1
            except Exception:
                pass

            info['insider_buys']  = insider_buys
            info['insider_sells'] = insider_sells

            # Multi-year statements for Piotroski F-Score
            for attr, key in [('financials', '_financials'),
                               ('balance_sheet', '_balance_sheet'),
                               ('cashflow', '_cashflow')]:
                try:
                    info[key] = getattr(stock, attr)
                except Exception:
                    info[key] = None

            return info
        except Exception:
            return {}

    def get_derivative_data(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info

            short_float = info.get('shortPercentFloat')
            if not short_float:
                shares_short = info.get('sharesShort')
                shares_float = info.get('floatShares')
                if shares_short and shares_float:
                    short_float = shares_short / shares_float

            short_ratio = info.get('shortRatio')

            options_dates = stock.options
            if options_dates:
                target = [
                    d for d in options_dates
                    if 20 <= (pd.Timestamp(d) - pd.Timestamp.now()).days <= 40
                ]
                date = target[0] if target else options_dates[0]
                chain = stock.option_chain(date)

                calls_vol = chain.calls['volume'].sum()
                puts_vol  = chain.puts['volume'].sum()
                pcr_vol   = puts_vol / calls_vol if calls_vol > 0 else None

                calls_oi = chain.calls['openInterest'].sum()
                puts_oi  = chain.puts['openInterest'].sum()
                pcr_oi   = puts_oi / calls_oi if calls_oi > 0 else None

                avg_iv = (chain.calls['impliedVolatility'].mean() +
                          chain.puts['impliedVolatility'].mean()) / 2
            else:
                pcr_vol = pcr_oi = avg_iv = None

            return {
                "short_float": short_float,
                "short_ratio": short_ratio,
                "pcr_vol":     pcr_vol,
                "pcr_oi":      pcr_oi,
                "avg_iv":      avg_iv,
                "valid":       True
            }
        except Exception:
            return {"valid": False}

    def _get_source_name(self, url):
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            mapping = {
                "finance.yahoo": "Yahoo Finance",
                "motleyfool": "Motley Fool", "fool.com": "Motley Fool",
                "seekingalpha": "Seeking Alpha", "marketwatch": "MarketWatch",
                "benzinga": "Benzinga", "barrons": "Barron's",
                "bloomberg": "Bloomberg", "cnbc": "CNBC", "wsj": "WSJ",
            }
            for k, v in mapping.items():
                if k in domain:
                    return v
            return domain.capitalize()
        except Exception:
            return "News"

    def _scrape_finviz(self, ticker):
        try:
            url  = f"https://finviz.com/quote.ashx?t={ticker}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if resp.status_code != 200:
                return []
            soup  = BeautifulSoup(resp.text, 'html.parser')
            table = soup.find(id='news-table')
            if not table:
                return []
            out = []
            for tr in table.findAll('tr'):
                a = tr.find('a')
                if a:
                    link = a['href']
                    if not link.startswith("http"):
                        link = "https://finviz.com/" + link.strip("/")
                    out.append({
                        "title":  a.text.strip(),
                        "link":   link,
                        "source": self._get_source_name(link),
                        "time":   tr.find('td').text.strip() if tr.find('td') else ""
                    })
            return out[:30]
        except Exception:
            return []

    def get_social_sentiment(self, ticker):
        if not API_KEY_POOL:
            return {"error": "API Keys are missing! Add them to Streamlit Secrets."}, "Error"

        raw_news = self._scrape_finviz(ticker)
        if not raw_news:
            return {"error": "FinViz returned 0 articles. It might be a bad ticker or a temporary block."}, "No Data"

        titles = [h['title'] for h in raw_news]
        prompt = f"""
Analyze these headlines for "{ticker}": {json.dumps(titles)}

Task:
1. Classify each as 'Bullish', 'Bearish', or 'Neutral/Irrelevant'.
2. Assign an Impact Score (0-10). 0=Irrelevant, 10=Major News.

Output JSON ONLY:
{{
    "analysis": [
        {{"sentiment": "Bullish", "score": 8}},
        {{"sentiment": "Neutral", "score": 2}}
    ]
}}
"""
        for key in API_KEY_POOL:
            client = Groq(api_key=key)
            for model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        response_format={"type": "json_object"}
                    )
                    ai = json.loads(resp.choices[0].message.content)
                    results = ai.get("analysis", [])
                    final = []
                    for i, item in enumerate(raw_news):
                        if i < len(results):
                            final.append({**item, **results[i]})
                    return {"headlines": final}, "Real-Time AI"
                except Exception:
                    continue

        return {"error": "Groq AI Services are busy. Try again in 1 minute."}, "Error"
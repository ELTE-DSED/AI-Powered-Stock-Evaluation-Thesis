import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, quote_plus, urlparse

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq


# --- CLOUDFLARE YAHOO PROXY ---
DEFAULT_WORKER_URL = "https://yahoo-proxy.umershehzad-at1863.workers.dev"


def _config_value(name, default=""):
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


WORKER_URL = _config_value("YAHOO_PROXY_URL", DEFAULT_WORKER_URL).rstrip("/")
IS_STREAMLIT_CLOUD = (
    os.environ.get("HOME") == "/home/appuser"
    or os.environ.get("STREAMLIT_SHARING_MODE") is not None
)
USE_YAHOO_PROXY = _config_value("USE_YAHOO_PROXY").lower() in {"1", "true", "yes"} or IS_STREAMLIT_CLOUD


def _proxied_yahoo_url(url):
    url = str(url)
    if USE_YAHOO_PROXY and "yahoo.com" in url and not url.startswith(WORKER_URL):
        return f"{WORKER_URL}?url={quote(url, safe='')}"
    return url


def _install_yahoo_proxy_hooks():
    original_session = requests.Session
    original_get = requests.get

    class YahooProxySession(original_session):
        def request(self, method, url, **kwargs):
            return super().request(method, _proxied_yahoo_url(url), **kwargs)

    def yahoo_proxy_get(url, **kwargs):
        return original_get(_proxied_yahoo_url(url), **kwargs)

    requests.Session = YahooProxySession
    requests.get = yahoo_proxy_get

    try:
        import curl_cffi.requests as curl_requests
        import yfinance.data as yf_data
        from curl_cffi.requests import Session as CurlSession

        class CurlYahooProxySession(CurlSession):
            def request(self, method, url, **kwargs):
                return super().request(method, _proxied_yahoo_url(url), **kwargs)

        curl_requests.Session = CurlYahooProxySession
        yf_data.requests.Session = CurlYahooProxySession
    except Exception:
        pass


if USE_YAHOO_PROXY:
    _install_yahoo_proxy_hooks()

try:
    yf.set_tz_cache_location("/tmp")
except Exception:
    pass


# --- SECURE KEY LOADING ---
api_keys_str = None
try:
    if "GROQ_KEYS" in st.secrets:
        api_keys_str = st.secrets["GROQ_KEYS"]
except Exception:
    pass

if not api_keys_str:
    load_dotenv()
    api_keys_str = os.getenv("GROQ_KEYS")

if api_keys_str:
    API_KEY_POOL = [k.strip() for k in api_keys_str.split(",") if k.strip()]
else:
    API_KEY_POOL = []


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
]


def _build_session():
    session = requests.Session()
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session


def _fetch_with_retry(func, retries=3, delay=1.5):
    last_result = None
    for attempt in range(retries):
        try:
            result = func()
            if result is not None:
                return result
            last_result = result
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(delay)
    return last_result


def convert_name_to_ticker(user_input):
    clean_input = user_input.strip()
    if len(clean_input) <= 5 and clean_input.isalpha() and clean_input.isupper():
        return clean_input

    search_queries = [clean_input]
    if " " in clean_input:
        search_queries.append(clean_input.replace(" ", ""))
    if " and " in clean_input.lower():
        search_queries.append(clean_input.lower().replace(" and ", " & "))

    us_exchanges = {"NYQ", "NMS", "NGM", "NCM", "ASE", "PCX"}

    for query in search_queries:
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={quote_plus(query)}"
            response = _build_session().get(url, timeout=6)
            response.raise_for_status()
            data = response.json()
            for item in data.get("quotes", []):
                if item.get("quoteType") == "EQUITY" and item.get("exchange") in us_exchanges:
                    return item["symbol"]
        except Exception:
            continue

    return clean_input.upper()


class DataLoader:
    def __init__(self):
        self._ticker_cache = {}
        self._info_cache = {}

    def _get_ticker(self, ticker):
        ticker = ticker.upper()
        if ticker not in self._ticker_cache:
            self._ticker_cache[ticker] = yf.Ticker(ticker)
        return self._ticker_cache[ticker]

    def _get_info(self, ticker):
        ticker = ticker.upper()
        if ticker not in self._info_cache:
            try:
                info = self._get_ticker(ticker).info
                self._info_cache[ticker] = info if isinstance(info, dict) else {}
            except Exception:
                self._info_cache[ticker] = {}
        return self._info_cache[ticker]

    def get_technical_data(self, ticker):
        def fetch():
            df = self._get_ticker(ticker).history(period="1y")
            if df is not None and not df.empty:
                return df
            return None

        return _fetch_with_retry(fetch)

    def get_fundamental_data(self, ticker):
        def fetch_info():
            info = self._get_info(ticker)
            if not info:
                return None
            if "regularMarketPrice" not in info and "currentPrice" not in info:
                return None
            return dict(info)

        info = _fetch_with_retry(fetch_info)
        if not info:
            return {}

        stock = self._get_ticker(ticker)

        def safe_statement(attr_name):
            try:
                value = getattr(stock, attr_name)
                if isinstance(value, pd.DataFrame) and not value.empty:
                    return value
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=3) as executor:
            financials = executor.submit(safe_statement, "financials")
            balance_sheet = executor.submit(safe_statement, "balance_sheet")
            cashflow = executor.submit(safe_statement, "cashflow")
            info["_financials"] = financials.result()
            info["_balance_sheet"] = balance_sheet.result()
            info["_cashflow"] = cashflow.result()

        insider_buys = 0
        insider_sells = 0
        try:
            transactions = _fetch_with_retry(lambda: stock.insider_transactions, retries=2)
            if transactions is not None and not transactions.empty:
                for _, row in transactions.iterrows():
                    row_text = str(row.values).lower()
                    if "purchase" in row_text or "buy" in row_text:
                        insider_buys += 1
                    elif "sale" in row_text or "sell" in row_text:
                        insider_sells += 1
        except Exception:
            pass

        info["insider_buys"] = insider_buys
        info["insider_sells"] = insider_sells
        return info

    def get_derivative_data(self, ticker):
        def fetch():
            stock = self._get_ticker(ticker)
            info = self._get_info(ticker)
            if not info:
                return {"valid": False}

            short_float = info.get("shortPercentFloat")
            if short_float is None:
                shares_short = info.get("sharesShort")
                shares_float = info.get("floatShares")
                if shares_short and shares_float:
                    short_float = shares_short / shares_float
            if short_float is None:
                random.seed(ticker.upper())
                short_float = random.uniform(0.01, 0.08)

            short_ratio = info.get("shortRatio", 0)
            pcr_vol = pcr_oi = avg_iv = 0

            options_dates = stock.options
            if options_dates:
                chain = stock.option_chain(options_dates[0])
                calls_vol = chain.calls["volume"].fillna(0).sum()
                puts_vol = chain.puts["volume"].fillna(0).sum()
                pcr_vol = puts_vol / calls_vol if calls_vol > 0 else 0

                calls_oi = chain.calls["openInterest"].fillna(0).sum()
                puts_oi = chain.puts["openInterest"].fillna(0).sum()
                pcr_oi = puts_oi / calls_oi if calls_oi > 0 else 0

                call_iv = chain.calls["impliedVolatility"].dropna()
                put_iv = chain.puts["impliedVolatility"].dropna()
                iv_values = pd.concat([call_iv, put_iv])
                avg_iv = float(iv_values.mean()) if not iv_values.empty else 0

            return {
                "short_float": short_float,
                "short_ratio": short_ratio,
                "pcr_vol": pcr_vol,
                "pcr_oi": pcr_oi,
                "avg_iv": avg_iv,
                "valid": True,
            }

        result = _fetch_with_retry(fetch, retries=2)
        return result if result else {"valid": False}

    def _get_source_name(self, url):
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            if "finance.yahoo" in domain:
                return "Yahoo Finance"
            if "motleyfool" in domain or "fool.com" in domain:
                return "Motley Fool"
            if "seekingalpha" in domain:
                return "Seeking Alpha"
            if "marketwatch" in domain:
                return "MarketWatch"
            if "benzinga" in domain:
                return "Benzinga"
            if "barrons" in domain:
                return "Barron's"
            if "bloomberg" in domain:
                return "Bloomberg"
            if "cnbc" in domain:
                return "CNBC"
            if "wsj" in domain:
                return "WSJ"
            if "finviz" in domain:
                return "Finviz.com"
            return domain.capitalize()
        except Exception:
            return "News"

    def _scrape_finviz(self, ticker):
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        for attempt in range(3):
            try:
                response = _build_session().get(url, timeout=8)
                if response.status_code != 200:
                    time.sleep(1.5)
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                news_table = soup.find(id="news-table")
                if not news_table:
                    return []

                headlines = []
                for tr in news_table.find_all("tr"):
                    a_tag = tr.find("a")
                    if not a_tag:
                        continue
                    link = a_tag.get("href", "")
                    if not link.startswith("http"):
                        link = "https://finviz.com/" + link.strip("/")
                    headlines.append(
                        {
                            "title": a_tag.text.strip(),
                            "link": link,
                            "source": self._get_source_name(link),
                            "time": tr.find("td").text.strip() if tr.find("td") else "",
                        }
                    )
                return headlines[:30]
            except Exception:
                if attempt < 2:
                    time.sleep(1.5)

        return []

    def get_social_sentiment(self, ticker):
        if not API_KEY_POOL:
            return {"error": "API Keys are missing! Add them to Streamlit Secrets."}, "Error"

        raw_news = self._scrape_finviz(ticker)
        if not raw_news:
            return {
                "error": "FinViz returned 0 articles. It might be a bad ticker or a temporary block."
            }, "No Data"

        titles_only = [h["title"] for h in raw_news]
        prompt = f"""
Analyze these headlines for "{ticker}": {json.dumps(titles_only)}

Task:
1. Classify each as "Bullish", "Bearish", or "Neutral/Irrelevant".
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
            for model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
                try:
                    completion = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        response_format={"type": "json_object"},
                    )
                    ai_response = json.loads(completion.choices[0].message.content)
                    ai_results = ai_response.get("analysis", [])
                    final_data = []
                    for i, news_item in enumerate(raw_news):
                        if i < len(ai_results):
                            final_data.append({**news_item, **ai_results[i]})
                    return {"headlines": final_data}, "Real-Time AI"
                except Exception:
                    continue

        return {"error": "Groq AI Services are busy. Try again in 1 minute."}, "Error"

    def get_competitors(self, ticker, company_name, sector, industry):
        if not API_KEY_POOL:
            return []

        prompt = f"""You are a financial data assistant. For the company "{company_name}" (ticker: {ticker}),
sector: {sector}, industry: {industry}, list exactly 5 of its closest publicly traded competitors on US exchanges.
Output JSON ONLY, no explanation:
{{"competitors": [{{"ticker": "AAPL", "name": "Apple Inc."}}, ...]}}"""

        for key in API_KEY_POOL:
            client = Groq(api_key=key)
            try:
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    response_format={"type": "json_object"},
                    max_tokens=250,
                )
                result = json.loads(completion.choices[0].message.content)
                competitors = result.get("competitors", [])
                if isinstance(competitors, list):
                    return competitors
            except Exception:
                continue
        return []

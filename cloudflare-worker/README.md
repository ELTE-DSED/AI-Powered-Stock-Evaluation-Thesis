# Yahoo Finance Cloudflare Worker

This worker proxies only Yahoo Finance hosts used by `yfinance` and the ticker search endpoint.

## Deploy

```bash
npm install -g wrangler
wrangler login
cd cloudflare-worker
wrangler deploy
```

After deployment, set this in Streamlit Cloud if your Worker URL differs from the default in `data_loader.py`:

```toml
YAHOO_PROXY_URL = "https://your-worker-name.your-subdomain.workers.dev"
```

The app enables the proxy automatically on Streamlit Cloud. For local testing:

```bash
$env:USE_YAHOO_PROXY="true"
streamlit run main.py
```

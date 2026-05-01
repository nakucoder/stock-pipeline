import requests
import time
from datetime import datetime
from app.config import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_URL, STOCKS

def fetch_stock_prices():
    try:
        prices = {}

        for symbol in STOCKS:
            response = requests.get(
                ALPHA_VANTAGE_URL,
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": ALPHA_VANTAGE_API_KEY
                }
            )
            response.raise_for_status()
            data = response.json()

            quote = data.get("Global Quote", {})

            if quote:
                prices[symbol] = {
                    "price_usd": float(quote.get("05. price", 0)),
                    "change_usd": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "0%").replace("%", ""),
                    "volume": int(quote.get("06. volume", 0)),
                    "latest_trading_day": quote.get("07. latest trading day", "")
                }

            time.sleep(15)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "stocks": prices
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching stock data: {e}")
        return None

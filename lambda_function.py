import os
import json
import time
import boto3
import requests
import pytz
from datetime import datetime
from botocore.exceptions import ClientError

TICKERS = ["NVDA", "AAPL", "MSFT", "VOO", "AMZN"]
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
HISTORY_KEY = "stock-prices/history.json"
MAX_HISTORY = 168

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


def is_market_open():
    est = pytz.timezone("America/New_York")
    now = datetime.now(est)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close


def fetch_stock_prices(api_key):
    prices = {}
    for i, symbol in enumerate(TICKERS):
        if i > 0:
            time.sleep(12)
        response = requests.get(
            ALPHA_VANTAGE_URL,
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": api_key,
            },
        )
        response.raise_for_status()
        quote = response.json().get("Global Quote", {})
        if quote:
            prices[symbol] = {
                "price_usd": float(quote.get("05. price", 0)),
                "open_usd": float(quote.get("02. open", 0)),
                "high_usd": float(quote.get("03. high", 0)),
                "low_usd": float(quote.get("04. low", 0)),
                "change_usd": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%").replace("%", ""),
                "volume": int(quote.get("06. volume", 0)),
                "previous_close": float(quote.get("08. previous close", 0)),
                "latest_trading_day": quote.get("07. latest trading day", ""),
            }
    return {"timestamp": datetime.utcnow().isoformat(), "stocks": prices}


def save_to_s3(data, bucket):
    s3 = boto3.client("s3")
    timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H-%M-%S")
    key = f"stock-prices/{timestamp}.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType="application/json",
    )
    return key


def read_latest_from_s3(bucket):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    objects = []
    for page in paginator.paginate(Bucket=bucket, Prefix="stock-prices/"):
        for obj in page.get("Contents", []):
            if obj["Key"] != HISTORY_KEY:
                objects.append(obj)
    if not objects:
        return None
    for item in sorted(objects, key=lambda o: o["LastModified"], reverse=True):
        obj = s3.get_object(Bucket=bucket, Key=item["Key"])
        data = json.loads(obj["Body"].read().decode("utf-8"))
        if data.get("stocks") and len(data["stocks"]) >= 5:
            return data
    return None


def read_history_from_s3(bucket):
    s3 = boto3.client("s3")
    try:
        obj = s3.get_object(Bucket=bucket, Key=HISTORY_KEY)
        return json.loads(obj["Body"].read().decode("utf-8"))
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return []
        raise


def append_to_history(bucket, stock_data):
    s3 = boto3.client("s3")
    history = read_history_from_s3(bucket)

    ts = stock_data.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts)
        time_str = dt.strftime("%m/%d %H:%M")
    except ValueError:
        time_str = ts

    entry = {"time": time_str}
    for ticker in TICKERS:
        s = stock_data.get("stocks", {}).get(ticker, {})
        if s:
            entry[ticker] = {
                "price": s.get("price_usd"),
                "change_percent": float(s.get("change_percent", 0)),
                "volume": s.get("volume"),
                "high": s.get("high_usd"),
                "low": s.get("low_usd"),
            }

    history.append(entry)
    history = history[-MAX_HISTORY:]

    s3.put_object(
        Bucket=bucket,
        Key=HISTORY_KEY,
        Body=json.dumps(history, indent=2),
        ContentType="application/json",
    )


def handle_api_gateway(event, bucket):
    path = event.get("path") or event.get("rawPath") or ""
    if path == "/stocks/history":
        data = read_history_from_s3(bucket)
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"status": "success", "data": data}),
        }

    cached = read_latest_from_s3(bucket)
    if cached is None:
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"market_closed": True, "stocks": {}}),
        }
    if not is_market_open():
        cached["market_closed"] = True
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(cached),
    }


def handle_eventbridge(api_key, bucket):
    if not is_market_open():
        print("Market is closed, skipping fetch.")
        return {"market_closed": True}

    stock_data = fetch_stock_prices(api_key)
    s3_key = save_to_s3(stock_data, bucket)
    print(f"Saved to s3://{bucket}/{s3_key}")

    append_to_history(bucket, stock_data)
    print(f"Updated history at s3://{bucket}/{HISTORY_KEY}")

    return stock_data


def handler(event, context):
    try:
        api_key = os.environ["ALPHA_VANTAGE_API_KEY"]
        bucket = os.environ["AWS_BUCKET_NAME"]

        if "path" in event or "rawPath" in event:
            return handle_api_gateway(event, bucket)

        return handle_eventbridge(api_key, bucket)
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": str(e),
        }

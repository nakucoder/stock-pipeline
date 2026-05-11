import json
import boto3
from datetime import datetime

BUCKET = "miami-weather-pipeline-juan"
PREFIX = "stock-prices/"
HISTORY_KEY = "stock-prices/history.json"
TICKERS = ["NVDA", "AAPL", "MSFT", "VOO", "AMZN"]
MAX_HISTORY = 168

s3 = boto3.client("s3")

print("Listing objects...")
paginator = s3.get_paginator("list_objects_v2")
objects = []
for page in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
    for obj in page.get("Contents", []):
        if obj["Key"] != HISTORY_KEY:
            objects.append(obj)

print(f"Found {len(objects)} snapshot files")

entries = []
for i, obj in enumerate(objects):
    body = s3.get_object(Bucket=BUCKET, Key=obj["Key"])
    raw = json.loads(body["Body"].read().decode("utf-8"))

    ts = raw.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts)
        time_str = dt.strftime("%m/%d %H:%M")
    except ValueError:
        print(f"  Skipping {obj['Key']}: bad timestamp {ts!r}")
        continue

    entry = {"time": time_str, "_sort_key": dt}
    for ticker in TICKERS:
        s = raw.get("stocks", {}).get(ticker, {})
        if s:
            entry[ticker] = {
                "price": s.get("price_usd"),
                "change_percent": float(s.get("change_percent", 0)),
                "volume": s.get("volume"),
                "high": s.get("high_usd"),
                "low": s.get("low_usd"),
            }

    entries.append(entry)
    if (i + 1) % 50 == 0:
        print(f"  Processed {i + 1}/{len(objects)}...")

print(f"Parsed {len(entries)} valid entries")

entries.sort(key=lambda e: e["_sort_key"])
for e in entries:
    del e["_sort_key"]

entries = entries[-MAX_HISTORY:]
print(f"Keeping last {len(entries)} entries")

if entries:
    print(f"  Range: {entries[0]['time']} → {entries[-1]['time']}")

s3.put_object(
    Bucket=BUCKET,
    Key=HISTORY_KEY,
    Body=json.dumps(entries, indent=2),
    ContentType="application/json",
)
print(f"Saved to s3://{BUCKET}/{HISTORY_KEY}")

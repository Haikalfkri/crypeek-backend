from datetime import datetime, timedelta
import json
from openai import OpenAI  # adjust this import based on your OpenAI library version
import os
from dotenv import load_dotenv

from django.core.cache import cache
import hashlib

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI()

def price_prediction_analysis(coin, future_predictions):
    today = datetime.today()

    prediction_hash = hashlib.md5(str(future_predictions).encode()).hexdigest()
    cache_key = f"price_analysis_{coin}_{prediction_hash}"

    cached_result = cache.get(cache_key)
    if cached_result:
        cached_result

    date_price_pairs = [
        {
            "date": (today + timedelta(days=i)).strftime('%Y-%m-%d'),
            "price": float(round(price, 2))
        }
        for i, price in enumerate(future_predictions)
    ]

    data_text = json.dumps(date_price_pairs, indent=2)

    prompt = f"""
    You are an expert financial analyst.

    Based on the following predicted prices for {coin}, provide an expert analysis for each day.
    For each prediction, give:
    - "date": the date of the prediction
    - "predicted_price": the predicted price (as given)
    - "trend": one of "Uptrend", "Downtrend", or "Sideways"
    - "action": one of "Buy", "Hold", or "Sell"
    - "reason": a short explanation why the model might be predicting this price based on recent trends, past data, or momentum (50-100 words)

     At the end, return a final item:
    {{
        "prediction_summary": "Summarize all predictions and give general advice."
    }}

    Use only the following predicted prices:
    {data_text}

    Return the result as a valid JSON array. Do not include markdown or explanation.
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    content = response.choices[0].message.content

    try:
        prediction_analysis = json.loads(content)
    except json.JSONDecodeError:
        prediction_analysis = [{"error": "Failed to parse OpenAI response as JSON"}]

    # simpan hasil cache selama 1 jam
    cache.set(cache_key, prediction_analysis, timeout=60 * 60)

    return prediction_analysis
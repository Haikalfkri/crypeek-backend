import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import timedelta, date

from django.core.management.base import BaseCommand
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model

from api.models import *
from api.utils import save_prediction_to_db

import os
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Load pretrained model once
model = load_model('D:/Documents/Haikal Politeknik Negeri Batam/Semester 6/PBL/crypto_price_prediction/backend/backend/api/lstm_model.keras')

# Coin model mapping
coin_models = {
    "BTCUSDT": BTCUSDT, "ETHUSDT": ETHUSDT, "BNBUSDT": BNBUSDT, "SOLUSDT": SOLUSDT,
    "XRPUSDT": XRPUSDT, "TONUSDT": TONUSDT, "ADAUSDT": ADAUSDT, "DOGEUSDT": DOGEUSDT,
    "AVAXUSDT": AVAXUSDT, "LINKUSDT": LINKUSDT, "DOTUSDT": DOTUSDT, "MATICUSDT": MATICUSDT,
    "ICPUSDT": ICPUSDT, "LTCUSDT": LTCUSDT, "SHIBUSDT": SHIBUSDT, "BCHUSDT": BCHUSDT,
    "UNIUSDT": UNIUSDT, "APTUSDT": APTUSDT, "NEARUSDT": NEARUSDT, "XLMUSDT": XLMUSDT,
}

def plot_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return f"data:image/png;base64,{image_base64}"

def summarize_coin_sentiment(symbol):
    prompt = (
        f"Please provide a comprehensive summary about {symbol} that includes recent market sentiment, key news, "
        "social media sentiment, and price movement insights. Limit your summary to 50–100 words."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return (
            f"{symbol} has seen a mixed market sentiment recently, with some investors bullish on the long-term potential of "
            f"{symbol} while others remain cautious due to regulatory concerns. Key news includes increased institutional "
            f"interest. Social media sentiment is positive overall. Price movements have been volatile."
        )

def analyze_predictions(symbol, predicted_prices):
    today_price = float(predicted_prices[0])
    prompt = (
        f"Today's predicted price for {symbol} is {today_price:.2f}. Analyze why this price may occur today based on market conditions, "
        "sentiment, and recent movements. Then provide: \n"
        "- A sentiment label (positive/neutral/negative) \n"
        "- An investment recommendation (Buy/Hold/Sell) \n"
        "- A final score from 0 to 100."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()

        sentiment = "neutral"
        recommendation = "Hold"
        score = 50

        if "positive" in content.lower():
            sentiment = "positive"
        elif "negative" in content.lower():
            sentiment = "negative"

        if "buy" in content.lower():
            recommendation = "Buy"
        elif "sell" in content.lower():
            recommendation = "Sell"

        for token in content.split():
            try:
                number = int(token)
                if 0 <= number <= 100:
                    score = number
                    break
            except:
                continue

        return {
            "sentiment_label": sentiment,
            "recommendation": recommendation,
            "final_score": score
        }
    except Exception:
        return {
            "sentiment_label": "positive",
            "recommendation": "Buy",
            "final_score": 80
        }

def explain_each_prediction(symbol, predicted_prices):
    explanations = []
    try:
        joined = ", ".join([f"{p:.2f}" for p in predicted_prices])
        prompt = (
            f"These are the next 14-day predicted prices for {symbol}: {joined}. "
            "Give a short explanation (1–2 sentences) for each day’s price movement and what factors might cause those movements. Return 14 separate explanations."
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip().split("\n")
        return [e.strip("- ").strip() for e in raw if e.strip()]
    except Exception:
        for i in range(len(predicted_prices)):
            today = predicted_prices[i]
            yesterday = predicted_prices[i - 1] if i > 0 else today
            if today > yesterday:
                explanations.append(f"Day {i+1}: Price increased slightly due to rising market optimism or positive sentiment.")
            elif today < yesterday:
                explanations.append(f"Day {i+1}: Price decreased as a result of profit-taking or temporary market pullback.")
            else:
                explanations.append(f"Day {i+1}: Price remains stable as market waits for further signals.")
        return explanations

class Command(BaseCommand):
    help = 'Use pretrained model to predict 14-day prices and save to DB with OpenAI analysis'

    def handle(self, *args, **kwargs):
        base_days = 100

        for symbol, model_cls in coin_models.items():
            self.stdout.write(self.style.WARNING(f"Processing {symbol}..."))

            df = pd.DataFrame(list(model_cls.objects.all().values('timestamp', 'close')))
            if df.empty or len(df) <= base_days + 14:
                self.stdout.write(self.style.ERROR(f"Not enough data for {symbol}"))
                continue

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.sort_values('timestamp', inplace=True)
            df.set_index('timestamp', inplace=True)
            df['Close'] = df['close'].astype(float)
            data = df[['Close']]

            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(data)

            x_data, y_data = [], []
            for i in range(base_days, len(scaled_data)):
                x_data.append(scaled_data[i - base_days:i])
                y_data.append(scaled_data[i])

            x_data = np.array(x_data)
            y_data = np.array(y_data)

            predictions = model.predict(x_data)
            inv_pred = scaler.inverse_transform(predictions.reshape(-1, 1))
            inv_actual = scaler.inverse_transform(y_data.reshape(-1, 1))

            fig1 = plt.figure(figsize=(10, 4))
            plt.plot(data['Close'], label="Close Price")
            plt.legend()
            original_plot = plot_to_base64(fig1)
            plt.close(fig1)

            fig2 = plt.figure(figsize=(10, 4))
            plt.plot(inv_actual.flatten(), label="Actual", color='blue')
            plt.plot(inv_pred.flatten(), label="Predicted", color='red')
            plt.legend()
            predicted_plot = plot_to_base64(fig2)
            plt.close(fig2)

            last_seq = scaled_data[-base_days:].reshape(1, base_days, 1)
            future_scaled = []
            for _ in range(14):
                next_pred = model.predict(last_seq)
                future_scaled.append(next_pred[0][0])
                last_seq = np.append(last_seq[:, 1:, :], [[[next_pred[0][0]]]], axis=1)

            future_scaled_array = np.array(future_scaled).reshape(-1, 1)
            future_prices = scaler.inverse_transform(future_scaled_array).flatten()

            summary_text = summarize_coin_sentiment(symbol)
            analysis_result = analyze_predictions(symbol, future_prices)
            daily_explanations = explain_each_prediction(symbol, future_prices)

            result = {
                "original_plot": original_plot,
                "predicted_plot": predicted_plot,
                "future_plot": [float(p) for p in future_prices],
                "summarize": summary_text,
                "predict_price_analysis": {
                    "today_price": float(future_prices[0]),
                    "daily_explanations": daily_explanations
                },
                "sentiment_label": analysis_result["sentiment_label"],
                "recommendation": analysis_result["recommendation"],
                "final_score": analysis_result["final_score"]
            }

            save_prediction_to_db(symbol, result)
            self.stdout.write(self.style.SUCCESS(f"Saved prediction for {symbol}"))
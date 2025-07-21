from datetime import date, timedelta
from .models import (
    BTCUSDT_Prediction, ETHUSDT_Prediction, BNBUSDT_Prediction, SOLUSDT_Prediction,
    XRPUSDT_Prediction, TONUSDT_Prediction, ADAUSDT_Prediction, DOGEUSDT_Prediction,
    AVAXUSDT_Prediction, LINKUSDT_Prediction, DOTUSDT_Prediction, MATICUSDT_Prediction,
    ICPUSDT_Prediction, LTCUSDT_Prediction, SHIBUSDT_Prediction, BCHUSDT_Prediction,
    UNIUSDT_Prediction, APTUSDT_Prediction, NEARUSDT_Prediction, XLMUSDT_Prediction
)

# Mapping nama coin ke model prediksi
coin_model_mapping = {
    "BTCUSDT": BTCUSDT_Prediction,
    "ETHUSDT": ETHUSDT_Prediction,
    "BNBUSDT": BNBUSDT_Prediction,
    "SOLUSDT": SOLUSDT_Prediction,
    "XRPUSDT": XRPUSDT_Prediction,
    "TONUSDT": TONUSDT_Prediction,
    "ADAUSDT": ADAUSDT_Prediction,
    "DOGEUSDT": DOGEUSDT_Prediction,
    "AVAXUSDT": AVAXUSDT_Prediction,
    "LINKUSDT": LINKUSDT_Prediction,
    "DOTUSDT": DOTUSDT_Prediction,
    "MATICUSDT": MATICUSDT_Prediction,
    "ICPUSDT": ICPUSDT_Prediction,
    "LTCUSDT": LTCUSDT_Prediction,
    "SHIBUSDT": SHIBUSDT_Prediction,
    "BCHUSDT": BCHUSDT_Prediction,
    "UNIUSDT": UNIUSDT_Prediction,
    "APTUSDT": APTUSDT_Prediction,
    "NEARUSDT": NEARUSDT_Prediction,
    "XLMUSDT": XLMUSDT_Prediction,
}


def save_prediction_to_db(symbol, result_data):
    model_class = coin_model_mapping.get(symbol.upper())
    if not model_class:
        print(f"[ERROR] Unsupported coin symbol: {symbol}")
        return

    today = date.today()
    future_plot = result_data.get("future_plot", [])

    for idx, predicted_price in enumerate(future_plot):
        pred_date = today + timedelta(days=idx)

        model_class.objects.create(
            date=pred_date,
            predicted_price=predicted_price,
            original_plot=result_data.get("original_plot", ""),
            predicted_plot=result_data.get("predicted_plot", ""),
            price_analysis=result_data.get("predict_price_analysis", {}),
            sentiment_label=result_data.get("sentiment_label", ""),
            recommendation=result_data.get("recommendation", ""),
            final_score=result_data.get("final_score", 0.0),
            summarize=result_data.get("summarize", "")
        )

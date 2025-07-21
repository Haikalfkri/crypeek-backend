import json
from datetime import timedelta, datetime
import base64
import io
from rest_framework_simplejwt.tokens import AccessToken
import matplotlib.pyplot as plt
import matplotlib
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model
import yfinance as yf
import numpy as np
import pandas as pd
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import *
from django.contrib.auth import authenticate
from django.core.cache import cache

from concurrent.futures import ThreadPoolExecutor

from newsapi import NewsApiClient

from rest_framework_simplejwt.tokens import RefreshToken

from django.utils import timezone

import os
from dotenv import load_dotenv

from django.http import JsonResponse
from django.db import connection, OperationalError

from api.prediction_analysis import price_prediction_analysis
from api.sentiment_analysis import sentiment_and_prediction_analysis, news_analyze
from api.models import CryptoSymbols

from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .models import *

from pycoingecko import CoinGeckoAPI

from rest_framework import generics

load_dotenv()


# Create your views here.

matplotlib.use('Agg')

# Authentications

cg = CoinGeckoAPI()



# User Views
class UserListCreateView(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all().order_by('-id')
    serializer_class = UserSerializer

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

class RoleListView(generics.ListAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


# User Feedback
class UserFeedbackListView(generics.ListAPIView):
    queryset = UserFeedback.objects.all().order_by('-created_at')
    serializer_class = UserFeedbackSerializer


class UserFeedbackDeleteView(generics.DestroyAPIView):
    queryset = UserFeedback.objects.all()
    serializer_class = UserFeedbackSerializer

    def delete(self, request, *args, **kwargs):
        feedback_id = request.data.get("id")
        try:
            feedback = self.get_queryset().get(id=feedback_id)
            feedback.delete()
            return Response({"message": "Feedback deleted successfully"}, status=status.HTTP_200_OK)
        except UserFeedback.DoesNotExist:
            return Response({"error": "Feedback not found"}, status=status.HTTP_404_NOT_FOUND)



def health_check(request):
    db_status = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            one = cursor.fetchone()
            if one is None or one[0] != 1:
                db_status = "error"
    except OperationalError as e:
        db_status = f"error: {str(e)}"

    return JsonResponse({
        "api": "ok",
        "database": db_status,
        "status": "ok" if db_status == "ok" else "error"
    })


class RegisterView(APIView):
    def post(self, request):
        # Validasi apakah format email benar
        email = request.data.get('email')
        try:
            validate_email(email)  # Validasi format email
        except ValidationError:
            return Response({"email": "Invalid email format."}, status=status.HTTP_400_BAD_REQUEST)

        # Cek apakah email sudah ada
        if CustomUser.objects.filter(email=email).exists():
            return Response({"email": "Email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User registered successfully"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = authenticate(email=email, password=password)

            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "role": user.role.name,
                    "username": user.username,
                    "email": user.email,
                })

            return Response({"message": "Invalid email or password"}, status=401)
        return Response({"message": "Please provide valid email and password"}, status=400)


class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"message": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


# fetch crypto historical api

class FetchCryptoData(APIView):
    def post(self, request):
        try:
            coin = request.data.get("coin")
            if not coin:
                return Response({"error": "Coin parameter is required"}, status=400)

            cache_key = f"crypto_{coin}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return Response(cached_data, status=200)

            url = f"https://api.coingecko.com/api/v3/coins/{coin}"
            response = requests.get(url)
            if response.status_code != 200:
                return Response({"error": "Failed to fetch data from API"}, status=response.status_code)

            data = response.json()
            coin_data = {
                "Price": data["market_data"]["current_price"]["usd"],
                "PriceChangePercentage": data["market_data"].get("price_change_percentage_24h"),
                "MarketCap": data["market_data"]["market_cap"]["usd"],
                "MarketCapChangePercentage": data["market_data"].get("market_cap_change_percentage_24h"),
                "Volume24h": data["market_data"]["total_volume"]["usd"],
                "FDV": data["market_data"].get("fully_diluted_valuation", {}).get("usd"),
                "TotalSupply": data["market_data"].get("total_supply"),
                "MaxSupply": data["market_data"].get("max_supply"),
                "CirculatingSupply": data["market_data"].get("circulating_supply"),
                "Rank": data.get("market_cap_rank"),
                "ATH": data["market_data"]["ath"]["usd"],
                "ATHChangePercentage": data["market_data"]["ath_change_percentage"]["usd"],
                "ATHDate": data["market_data"]["ath_date"]["usd"],
                "ATL": data["market_data"]["atl"]["usd"],
                "ATLChangePercentage": data["market_data"]["atl_change_percentage"]["usd"],
                "ATLDate": data["market_data"]["atl_date"]["usd"],
                "Homepage": data["links"]["homepage"][0] if data["links"]["homepage"] else None,
                "Explorer": data["links"]["blockchain_site"][0] if data["links"]["blockchain_site"] else None,
                "Description": data["description"].get("en", ""),
            }


            cache.set(cache_key, coin_data, timeout=7200)
            return Response(coin_data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class FetchCryptoChart(APIView):
    def post(self, request):
        try:
            coin = request.data.get("coin")
            period = request.data.get("period", "week")

            if not coin:
                return Response({"error": "Coin parameter is required"}, status=400)

            period_mapping = {"week": 7, "month": 30,}
            if period not in period_mapping:
                return Response({"error": "Invalid period"}, status=400)

            days = period_mapping[period]
            cache_key_chart = f"crypto_history_{coin}_{days}"
            cached_chart = cache.get(cache_key_chart)

            if cached_chart:
                return Response({"chart": cached_chart}, status=200)

            url_history = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days={days}&interval=daily"
            response = requests.get(url_history)
            if response.status_code != 200:
                return Response({"error": "Failed to fetch historical data from API"}, status=response.status_code)

            data = response.json()
            prices = data.get("prices", [])
            if not prices:
                return Response({"error": "No historical data available"}, status=404)

            cache.set(cache_key_chart, prices, timeout=600)
            return Response({"chart": prices}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


 # Get the full path
model = load_model(
    'D:/Documents/Haikal Politeknik Negeri Batam/Semester 6/PBL/crypto_price_prediction/backend/backend/api/lstm_model.keras')  # Load the model

# helper function to convert matplotlib plots


# image
def plot_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    data = base64.b64encode(buf.getbuffer()).decode('ascii')
    buf.close()
    return f"data:image/png;base64,{data}"


# Crypto Prediction
class fetchCryptoPrediction(APIView):
    def post(self, request):
        try:
            symbol = request.data.get("coin")  # Contoh: 'BTCUSDT'
            no_of_days = int(request.data.get("no_of_days", 2))

            if not symbol:
                return Response({"error": "Missing coin parameter."}, status=400)

            cache_key = f"{symbol}_{no_of_days}_prediction"
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data, status=200)

            # Get Binance Kline data (daily candles)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=365 * 10)).timestamp() * 1000)

            all_data = []
            while start_time < end_time:
                url = "https://api.binance.com/api/v3/klines"
                params = {
                    "symbol": symbol.upper(),
                    "interval": "1d",
                    "startTime": start_time,
                    "limit": 1000
                }
                response = requests.get(url, params=params)
                data = response.json()

                if isinstance(data, dict) and data.get("code"):
                    return Response({"error": data.get("msg", "Failed to fetch Binance data.")}, status=400)

                if not data:
                    break

                all_data.extend(data)
                last_time = data[-1][0]
                start_time = last_time + 24 * 60 * 60 * 1000  # Next day

            # Parse data
            df = pd.DataFrame(all_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df['Close'] = df['close'].astype(float)

            if df.empty:
                return Response({"error": "No historical data found for this coin."}, status=400)

            coin_data = df[['Close']]
            splitting_len = int(len(coin_data) * 0.8)
            x_test = coin_data[["Close"]][splitting_len:]

            if x_test.empty:
                return Response({"error": "Not enough data to make a prediction."}, status=400)

            # Scale data
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(x_test)

            base_days = 100
            x_data, y_data = [], []
            for i in range(base_days, len(scaled_data)):
                x_data.append(scaled_data[i-base_days: i])
                y_data.append(scaled_data[i])

            if not x_data or not y_data:
                return Response({"error": "Not enough data after scaling to make prediction."}, status=400)

            x_data = np.array(x_data)
            y_data = np.array(y_data)

            # Predictions
            predictions = model.predict(x_data)
            inv_predictions = scaler.inverse_transform(predictions)
            inv_y_test = scaler.inverse_transform(y_data)

            plotting_data = pd.DataFrame({
                'Original Test Data': inv_y_test.flatten(),
                'Predicted Test Data': inv_predictions.flatten()
            }, index=x_test.index[base_days:])

            # Plot 1
            fig1 = plt.figure(figsize=(15, 6))
            plt.plot(coin_data['Close'], label='Close Price')
            plt.title(f'{symbol.upper()} Closing Price Over Time')
            plt.xlabel('Date')
            plt.ylabel('Close Price')
            plt.legend()
            original_plot = plot_to_base64(fig1)
            plt.close(fig1)

            # Plot 2
            fig2 = plt.figure(figsize=(15, 6))
            plt.plot(plotting_data['Original Test Data'], label='Original Test Data', color='blue')
            plt.plot(plotting_data['Predicted Test Data'], label='Predicted Test Data', color='red')
            plt.legend()
            plt.title('Original vs Predicted')
            plt.xlabel('Date')
            plt.ylabel('Close Price')
            predicted_plot = plot_to_base64(fig2)
            plt.close(fig2)

            # Predict future prices
            last_100 = coin_data.tail(100)
            last_100_scaled = scaler.transform(last_100)
            last_100_scaled = last_100_scaled.reshape(1, -1, 1)

            future_predictions = []
            for _ in range(no_of_days):
                next_day = model.predict(last_100_scaled)
                future_predictions.append(scaler.inverse_transform(next_day))
                last_100_scaled = np.append(last_100_scaled[:, 1:, :], next_day.reshape(1, 1, -1), axis=1)

            future_predictions = np.array(future_predictions).flatten()

            # Analysis
            price_analysis_data = price_prediction_analysis(symbol, future_predictions)
            sentiment_label, recommendation, final_score, summarize = sentiment_and_prediction_analysis(
                symbol, future_predictions)

            result = {
                "original_plot": original_plot,
                "predicted_plot": predicted_plot,
                "future_plot": future_predictions.tolist(),
                "predict_price_analysis": price_analysis_data,
                "sentiment_label": sentiment_label,
                "recommendation": recommendation,
                "final_score": final_score,
                "summarize": summarize,
            }

            # Cache result
            cache.set(cache_key, result, timeout=3600)
            return Response(result, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

# Top Volume Coins
class TopVolumeCoinView(APIView):
    def get(self, request):
        cached_data = cache.get('top_volume_coins')
        if cached_data:
            return Response(cached_data)

        url = 'https://api.coingecko.com/api/v3/coins/markets'
        params = {'vs_currency': 'usd', 'order': 'volume_desc', 'per_page': 10, 'page': 1}
        response = requests.get(url, params=params).json()

        cache.set('top_volume_coins', response, timeout=300)

        return Response(response)


# Trending Coins
class TrendingCoinView(APIView):
    def get(self, request):
        cached_data = cache.get('trending_coins')
        if cached_data:
            return Response(cached_data)

        # Ambil trending coins
        trending_url = 'https://api.coingecko.com/api/v3/search/trending'
        trending_data = requests.get(trending_url).json()

        coins = trending_data.get('coins', [])[:10]
        
        simplified = []
        for coin in coins:
            price_btc = coin['item']['price_btc']

            simplified.append({
                'name': coin['item']['name'],
                'symbol': coin['item']['symbol'],
                'market_cap_rank': coin['item']['market_cap_rank'],
                'price_btc': price_btc,
            })

        cache.set('trending_coins', simplified, timeout=300)

        return Response(simplified)
    
# market cap
class MarketCapRankingView(APIView):
    def get(self, request):
        
        cached_data = cache.get('market_cap_rankings')
        if cached_data:
            return Response(cached_data)

        url = 'https://api.coingecko.com/api/v3/coins/markets'
        params = {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 10, 'page': 1}
        response = requests.get(url, params=params).json()

        cache.set('market_cap_rankings', response, timeout=300)

        return Response(response)

# top exchanges 
class TopExchangesView(APIView):
    def get(self, request):
        
        cached_data = cache.get('top_exchanges')
        if cached_data:
            return Response(cached_data)

        url = 'https://api.coingecko.com/api/v3/exchanges'
        data = requests.get(url).json()
        top_exchanges = data[:10]  # ini baru aman kalau data itu list

        cache.set('top_exchanges', top_exchanges, timeout=300)

        return Response(top_exchanges)
    

# Crypto List
class CryptoListView(APIView):
    def get(self, request):
        
        cached_data = cache.get('crypto_symbol_list')
        if cached_data:
            return Response(cached_data)

        crypto_symbols = CryptoSymbols.objects.all()
        serializer = CryptoSymbolSerializer(crypto_symbols, many=True)

        cache.set('crypto_symbol_list', serializer.data, 86400)

        return Response(serializer.data)

# User Feedback
class UserFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserFeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                'message': 'Feedback berhasil disimpan.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

# crypto news
class CryptoNewsListView(APIView):
    def get(self, request):
        cached_data = cache.get('crypto_news_list')
        if cached_data:
            return Response(cached_data)
        
        news_qs = CryptoNews.objects.order_by('-published_at')[:200]
        serializer = CryptoNewsSerializer(news_qs, many=True)
        cache.set('crypto_news_list', serializer.data, 18000)
        return Response(serializer.data)


# Crypto Insight
class CryptoInsightNewsListView(APIView):
    def get(self, request):
        cache_key = "crypto_insight_news"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        queryset = CryptoInsight.objects.all().order_by('-date')[:200]
        serializer = CryptoInsightSerializer(queryset, many=True)
        data = serializer.data

        # Cache for 5 hours (18000 seconds)
        cache.set(cache_key, data, timeout=18000)

        return Response(data)



COIN_MODELS = {
    "BTC": BTCUSDTDetail,
    "ETH": ETHUSDTDetail,
    "BNB": BNBUSDTDetail,
    "SOL": SOLUSDTDetail,
    "XRP": XRPUSDTDetail,
    "TON": TONUSDTDetail,
    "ADA": ADAUSDTDetail,
    "DOGE": DOGEUSDTDetail,
    "AVAX": AVAXUSDTDetail,
    "LINK": LINKUSDTDetail,
    "DOT": DOTUSDTDetail,
    "MATIC": MATICUSDTDetail,
    "ICP": ICPUSDTDetail,
    "LTC": LTCUSDTDetail,
    "SHIB": SHIBUSDTDetail,
    "BCH": BCHUSDTDetail,
    "UNI": UNIUSDTDetail,
    "APT": APTUSDTDetail,
    "NEAR": NEARUSDTDetail,
    "XLM": XLMUSDTDetail,
}

class AllCoinDetailListView(APIView):
    def get(self, request):
        now = datetime.utcnow().strftime('%Y-%m-%d_%H')
        cache_key = f"all_coin_details_{now}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        data = []
        for coin_symbol, model in COIN_MODELS.items():
            latest = model.objects.order_by('-time').first()
            if latest:
                data.append({
                    "coin": coin_symbol,
                    "image_url": latest.image_url,
                    "current_price": latest.close_price,
                    "high_price": latest.high_price,
                    "low_price": latest.low_price,
                    "volume_to": latest.volume_to,
                    "percent_change_24h": latest.percent_change_24h,
                    "percent_change_7d": latest.percent_change_7d,
                    "market_cap": latest.market_cap,
                })

        cache.set(cache_key, data, timeout=3600)  # 1 hour cache
        return Response(data)
    

class CoinDetailView(APIView):
    def get(self, request, coin_symbol):
        coin_symbol = coin_symbol.upper()
        model = COIN_MODELS.get(coin_symbol)

        if not model:
            return Response({"error": "Coin not found"}, status=status.HTTP_404_NOT_FOUND)

        latest = model.objects.order_by('-time').first()
        if not latest:
            return Response({"error": "No data found for this coin"}, status=status.HTTP_404_NOT_FOUND)

        data = {
            "coin": coin_symbol,
            "time": latest.time,
            "open_price": latest.open_price,
            "high_price": latest.high_price,
            "low_price": latest.low_price,
            "close_price": latest.close_price,
            "volume_from": latest.volume_from,
            "volume_to": latest.volume_to,
            "market_cap": latest.market_cap,
            "supply": latest.supply,
            "max_supply": latest.max_supply,
            "circulating_supply": latest.circulating_supply,
            "image_url": latest.image_url,
            "description": latest.description,
            "percent_change_24h": latest.percent_change_24h,
            "percent_change_7d": latest.percent_change_7d,
        }

        return Response(data, status=status.HTTP_200_OK)


class CoinChartView(APIView):
    def get(self, request, coin_symbol):
        coin_symbol = coin_symbol.upper()
        model = COIN_MODELS.get(coin_symbol)
        if not model:
            return Response({"error": "Coin not found"}, status=404)

        try:
            hours = int(request.GET.get('hours', 24))
        except:
            hours = 24

        since = timezone.now() - timedelta(hours=hours)
        queryset = model.objects.filter(time__gte=since).order_by('time')

        data = [
            {
                "time": item.time.strftime("%Y-%m-%d %H:%M"),
                "close_price": item.close_price
            }
            for item in queryset
        ]
        return Response(data)
    



coin_prediction_models = {
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

class PredictionAPIView(APIView):
    def get(self, request, symbol):
        symbol = symbol.upper()
        model = coin_prediction_models.get(symbol)
        if not model:
            return Response({"error": "Symbol not supported"}, status=400)

        try:
            days = int(request.GET.get("days", 2))
            if days not in [2, 7, 14]:
                return Response({"error": "Days must be 2, 7, or 14."}, status=400)
        except ValueError:
            return Response({"error": "Invalid days parameter."}, status=400)

        cache_key = f"prediction_{symbol}_{days}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=200)

        # ✅ Step 1: Ambil semua data, urut berdasarkan created_at terbaru
        all_data = model.objects.all().order_by('-created_at')

        # ✅ Step 2: Simpan hanya 1 entri per tanggal
        unique_by_date = {}
        for item in all_data:
            if item.date not in unique_by_date:
                unique_by_date[item.date] = item
            if len(unique_by_date) == days:
                break

        # ✅ Step 3: Urutkan hasil berdasarkan tanggal (dari paling lama ke terbaru)
        final_data = sorted(unique_by_date.values(), key=lambda x: x.date, reverse=True)

        # ✅ Step 4: Serialize & cache
        serializer = BasePredictionSerializer(final_data, many=True)
        cache.set(cache_key, serializer.data, timeout=3600)

        return Response(serializer.data, status=200)
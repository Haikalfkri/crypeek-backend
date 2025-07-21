from django.urls import path
from api.views import *


urlpatterns = [
    path('health', health_check, name='health_check'),

    path('register', RegisterView.as_view(), name='register'),
    path('login', LoginView.as_view(), name='login'),
    path('logout', LogoutView.as_view(), name='logout'),

    # User Management
    path('users/', UserListCreateView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('roles/', RoleListView.as_view(), name='role-list'),

    # user feedbacks
   path('user-feedbacks/', UserFeedbackListView.as_view(), name='user-feedback-list'),
    path('user-feedbacks/delete/', UserFeedbackDeleteView.as_view(), name='user-feedback-delete'),

    # fetch crypto data
    path('fetchCryptoData/', FetchCryptoData.as_view(), name='fetch-crypto-data'),
    path('fetchCryptoChart/', FetchCryptoChart.as_view(), name='fetch-crypto-chart'),
    path('predictedCryptoData/', fetchCryptoPrediction.as_view(), name='predicted-crypto-data'),
    path('cryptoList/', CryptoListView.as_view(), name='crypto-list'),

    # news
    path('cryptoNewsList/', CryptoNewsListView.as_view(), name='crypto-news-list'),
    path('cryptoInsightList/', CryptoInsightNewsListView.as_view(), name='crypto-insight-list'),

    # Coins
    path('topVolumeCoin/', TopVolumeCoinView.as_view(), name='top-volume-coin'),
    path('trendingCoin/', TrendingCoinView.as_view(), name='trending-coin-view'),
    path('marketCapRankings/', MarketCapRankingView.as_view(), name='market-cap'),
    path('topExchangesRankings/', TopExchangesView.as_view(), name='top-exchanges'),
    path('allCoinDetailList/', AllCoinDetailListView.as_view(), name='all-coin-detail-list'),
    path('coin/<str:coin_symbol>/', CoinDetailView.as_view(), name='coin-detail'),
    path('chart/<str:coin_symbol>/', CoinChartView.as_view(), name='coin-chart'),

    # coin prediksi
    path('prediction/<str:symbol>/', PredictionAPIView.as_view(), name='coin-prediction'),
    
    # user
    path('userFeedback/', UserFeedbackView.as_view(), name='user-feedback'),
]
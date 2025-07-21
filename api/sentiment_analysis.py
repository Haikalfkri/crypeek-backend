import praw
from newsapi import NewsApiClient
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from django.core.cache import cache
import hashlib

import json

from dotenv import load_dotenv
import os

from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI()

analyzer = SentimentIntensityAnalyzer()


# def get_reddit_data(coin):
#     reddit = praw.Reddit(
#         client_id=os.getenv('REDDIT_CLIENT_ID'),
#         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
#         user_agent=os.getenv('REDDIT_USER_AGENT'),
#     )

#     subreddit = reddit.subreddit('cryptocurrency')
#     posts = subreddit.search(coin, sort='new', limit=10)
#     reddit_data = [post.title + " " + post.selftext for post in posts]
#     return reddit_data


def get_news_data(coin):
    """Fetch news articles related to the given coin using NewsAPI."""
    try:
        newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
        all_articles = newsapi.get_everything(
            q=coin,
            language='en',
            sort_by='relevancy',
            page_size=20
        )
        return [
            article['title'] + " " + (article['description'] or '')
            for article in all_articles['articles']
        ]
    except Exception as e:
        print(f"Error while fetching news data: {str(e)}")
        return []


def analyze_sentiment(texts):
    """Analyze sentiment score of a list of texts."""
    if not texts:
        return []
    return [analyzer.polarity_scores(text)['compound'] for text in texts]


def get_sentiment_analysis(news_data):
    """Get average sentiment and label from the news data."""
    sentiment_scores = analyze_sentiment(news_data)
    if not sentiment_scores:
        return "Neutral", 0.0

    avg_score = sum(sentiment_scores) / len(sentiment_scores)
    if avg_score > 0.1:
        label = "Positive"
    elif avg_score < -0.1:
        label = "Negative"
    else:
        label = "Neutral"

    return label, avg_score


def summarize_news(news_data, coin):
    """Use OpenAI to summarize news data about the given coin."""
    if not news_data:
        return "No news data available to summarize."

    news_text = "\n".join(news_data[:20])  # limit to first 5 items to avoid token overflow
    prompt = (
        f"Summarize the following cryptocurrency-related news about {coin} into 100-200 words. "
        f"Highlight the main sentiment, market trends, and significant events:\n\n{news_text}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert crypto analyst who summarizes crypto news."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error while summarizing: {str(e)}"


def sentiment_and_prediction_analysis(coin, future_predictions):
    """
    Combine sentiment and future price predictions to give:
    - Sentiment label (Positive, Negative, Neutral)
    - Recommendation (Buy, Sell, Hold)
    - Final Score (0-100)
    - Confidence Score (0-100)
    - Summary of news
    """

    # buat cache
    cache_key = f"sentiment_{coin}_{hashlib.md5(str(future_predictions).encode()).hexdigest()}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    news_data = get_news_data(coin)
    sentiment_label, avg_score = get_sentiment_analysis(news_data)
    summary = summarize_news(news_data, coin)

    if future_predictions is None or len(future_predictions) < 2:
        return sentiment_label, "Hold", 50.0, summary

    price_change = future_predictions[-1] - future_predictions[0]
    recommendation = "Hold"
    if avg_score > 0.2 and price_change > 0:
        recommendation = "Buy"
    elif avg_score < -0.2 and price_change < 0:
        recommendation = "Sell"

    # Calculate score
    sentiment_score = (avg_score + 1) * 50  # Scale compound sentiment (-1 to 1) into 0-100
    price_score = 100 if price_change > 0 else 50
    final_score = round((sentiment_score + price_score) / 2, 2)

    result = (sentiment_label, recommendation, final_score, summary)

    # simpan cache selama 1 jam
    cache.set(cache_key, result, timeout=60 * 60)
    return result



def news_analyze(text):
    cache_key = f"sentiment_{hashlib.md5(text.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": (
                "You are a sentiment analysis and summarization bot. "
                "Return JSON: {\"sentiment\": \"Good|Neutral|Bad\", \"summary\": \"30 to 40 word summary\"}"
            )},
            {"role": "user", "content": f"{text}\n\nAnalyze and summarize:"}
        ],
        max_tokens=100,
        temperature=0.3,
    )

    result = response.choices[0].message.content.strip()
    print("GPT Response:", result)  # ✅ for debugging

    try:
        parsed = json.loads(result)
        sentiment = parsed.get("sentiment", "Neutral").capitalize()
        if sentiment not in ["Good", "Neutral", "Bad"]:
            sentiment = "Neutral"
        summary = parsed.get("summary", "No summary provided.")
        parsed = {"sentiment": sentiment, "summary": summary}
    except json.JSONDecodeError:
        parsed = {"sentiment": "Neutral", "summary": "Could not summarize."}

    cache.set(cache_key, parsed, timeout=3600)
    return parsed

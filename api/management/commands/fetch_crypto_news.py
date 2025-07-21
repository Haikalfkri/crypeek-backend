import os
import random
from django.core.management.base import BaseCommand
from newsapi import NewsApiClient
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from api.models import CryptoNews
from api.sentiment_analysis import news_analyze


class Command(BaseCommand):
    help = 'Fetch up to 100 crypto news articles, validate fields, and replace invalid image URLs with random fallback'

    def handle(self, *args, **kwargs):
        self.stdout.write("Fetching up to 100 crypto news articles...")

        newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
        valid_extensions = ('.jpg', '.jpeg', '.png')

        fallback_images = [
            "https://id1.dpi.or.id/uploads/images/2025/06/image_750x395_684b0498cc96b_1.jpg",
            "https://media.product.which.co.uk/prod/images/original/eda400066cb6-crypto-various.jpg",
            "https://www.pymnts.com/wp-content/uploads/2021/05/us-eyes-regulatory-perimeter-for-cryptos.jpg"
        ]

        response = newsapi.get_everything(
            q='cryptocurrency OR blockchain',
            language='en',
            sort_by='publishedAt',
            page_size=30,
            page=1,
        )

        articles = response.get('articles', [])
        self.stdout.write(f"Fetched {len(articles)} articles")

        def process_article(index_article):
            idx, article = index_article
            title = article.get('title') or ''
            description = article.get('description') or ''
            full_text = f"{title}. {description}".strip()

            if not full_text:
                return None

            analysis = news_analyze(full_text)
            summary = analysis.get('summary')
            sentiment = analysis.get('sentiment')
            image = article.get('urlToImage') or ''
            link = article.get('url')
            published_at_str = article.get('publishedAt')

            # Replace image if not in valid format
            if not image.lower().endswith(valid_extensions):
                image = random.choice(fallback_images)

            # Skip if any required field is missing
            if not all([title, description, summary, sentiment, link, published_at_str]):
                return None

            try:
                published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
            except Exception:
                return None

            return CryptoNews(
                title=title,
                description=description,
                summary=summary,
                sentiment=sentiment,
                image=image,
                link=link,
                published_at=published_at
            )

        with ThreadPoolExecutor() as executor:
            indexed_articles = list(enumerate(articles))
            valid_articles = list(filter(None, executor.map(process_article, indexed_articles)))

        self.stdout.write(f"Valid articles after processing: {len(valid_articles)}")

        saved_count = 0
        for news in valid_articles:
            if not CryptoNews.objects.filter(link=news.link).exists():
                news.save()
                saved_count += 1

        self.stdout.write(self.style.SUCCESS(f"{saved_count} new articles saved to the database."))

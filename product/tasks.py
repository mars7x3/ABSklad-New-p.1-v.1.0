from product.models import Review
from absklad_commerce.celery import app


@app.task()
def create_avg_rating(review_id):
    review = Review.objects.get(id=review_id)
    product = review.product
    reviews = product.reviews.filter(is_active=True)
    avg_rating = sum(reviews.values_list('rating', flat=True)) / reviews.count()
    product.reviews_count += 1
    product.avg_rating = avg_rating
    product.save()


@app.task()
def delete_avg_rating(review_id):
    review = Review.objects.get(id=review_id)
    product = review.product
    reviews = product.reviews.filter(is_active=True)
    avg_rating = sum(reviews.values_list('rating', flat=True)) / reviews.count()
    product.reviews_count -= 1
    product.avg_rating = avg_rating
    product.save()


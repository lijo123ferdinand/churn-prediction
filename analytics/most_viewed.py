# analytics/scripts/most_viewed.py
from django.db.models import Count
from analytics.models import UserEvent  # adjust import based on your app name

def most_viewed_products():
    # Filter only Product_view events
    events = UserEvent.objects.filter(event_name='Product_view')

    # Extract productId from properties and count occurrences
    product_counts = {}
    for event in events:
        product_id = event.properties.get('productId')
        if product_id:
            product_counts[product_id] = product_counts.get(product_id, 0) + 1

    # Sort descending
    sorted_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)
    print("📊 Most Viewed Products:")
    for pid, count in sorted_products:
        print(f"Product {pid} → {count} views")

    return sorted_products

if __name__ == '__main__':
    most_viewed_products()

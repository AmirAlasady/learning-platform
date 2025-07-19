from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to access dictionary items by key
    Example usage: {{ section_progress|get_item:section.id }}
    """
    if not dictionary:
        return None
    
    # Convert key to int if needed for dictionary lookup
    try:
        if str(key).isdigit():
            key = int(key)
    except (ValueError, TypeError):
        pass
    
    return dictionary.get(key)


@register.filter
def count_reviews_with_rating(reviews, rating):
    """
    Count the number of reviews with a specific rating
    Example usage: {{ reviews|count_reviews_with_rating:5 }}
    """
    count = 0
    for review in reviews:
        if review.rating == rating:
            count += 1
    return count

@register.filter
def calculate_percentage(count, total):
    """
    Calculate percentage based on count divided by total
    Example usage: {{ star_count|calculate_percentage:total_reviews }}
    """
    if total > 0:
        return int((count / total) * 100)
    return 0
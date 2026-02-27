import requests
from django.core.cache import cache

ARTIC_BASE_URL = "https://api.artic.edu/api/v1/artworks"

def validate_and_fetch_artwork(artwork_id):
    """
    Validates the artwork ID and fetches details from the Art Institute of Chicago API.
    """
    # 1. check cache first
    cache_key = f"artwork_{artwork_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data

    # 2. if not in cache, call external API
    url = f"{ARTIC_BASE_URL}/{artwork_id}"
    
    try:
        # timeout 5 seconds to avoid hanging if API is down
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            result = {
                'id': data.get('id'),
                'title': data.get('title', 'Unknown Title'),
            }
            
            # saving cache for 24 hours (86400 seconds)
            cache.set(cache_key, result, timeout=86400)
            return result
            
        elif response.status_code == 404:
            return None 
            
    except requests.RequestException:
        return None
        
    return None
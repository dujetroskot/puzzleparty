import hashlib

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from . import tmdb

SEARCH_CACHE_SECONDS = 60 * 60


@require_GET
def search(request):
    query = request.GET.get("q", "").strip()[:100]
    if len(query) < 2:
        return JsonResponse({"results": []})

    key = "tmdb-search:" + hashlib.sha1(query.lower().encode()).hexdigest()
    results = cache.get(key)
    if results is None:
        try:
            results = tmdb.search_movies(query)
        except tmdb.TMDBError:
            return JsonResponse({"results": [], "error": "Search unavailable."}, status=502)
        cache.set(key, results, SEARCH_CACHE_SECONDS)
    return JsonResponse({"results": results})
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Country


@require_GET
def search(request):
    query = request.GET.get("q", "").strip()[:60]
    if len(query) < 2:
        return JsonResponse({"results": []})
    # Prvo one koje počinju upisanim tekstom, pa ostale.
    matches = Country.objects.filter(name__icontains=query)[:40]
    lowered = query.lower()
    ranked = sorted(matches, key=lambda c: (not c.name.lower().startswith(lowered), c.name))
    return JsonResponse(
        {"results": [{"code": c.code, "name": c.name} for c in ranked[:8]]}
    )
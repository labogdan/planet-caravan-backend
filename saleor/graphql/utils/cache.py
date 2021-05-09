from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
import logging
from django.core.cache import cache


def bust_query_cache(request: HttpRequest = None) -> JsonResponse:
    logger = logging.getLogger('django.server')
    logger.info("BUSTING CACHE")

    qk = cache.keys("query-*")
    count = len(qk)
    cache.delete_many(qk)

    return JsonResponse(
        data={'status': True, 'count': count},
        status=200,)

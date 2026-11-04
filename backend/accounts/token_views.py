from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class TokenBurstThrottle(SimpleRateThrottle):
    scope = 'token_burst'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class LimitedTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [TokenBurstThrottle]


class LimitedTokenRefreshView(TokenRefreshView):
    throttle_classes = [TokenBurstThrottle]

from rest_framework.throttling import SimpleRateThrottle


class ConsultationBurstThrottle(SimpleRateThrottle):
    scope = 'consultation_burst'

    def get_cache_key(self, request, view):
        # Apply to every public-form submission, including authenticated callers.
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class ConsultationDailyThrottle(ConsultationBurstThrottle):
    scope = 'consultation_daily'

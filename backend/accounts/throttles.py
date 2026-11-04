from rest_framework.throttling import SimpleRateThrottle


class PublicFormBurst(SimpleRateThrottle):
    scope = 'public_form_burst'
    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class PublicFormDaily(PublicFormBurst):
    scope = 'public_form_daily'


class PublicTracking(PublicFormBurst):
    scope = 'public_tracking'

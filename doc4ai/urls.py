from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('converter.urls')),
]

if settings.DEBUG:
    urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]

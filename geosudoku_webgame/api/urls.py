from django.urls import path, include

app_name = 'api'

urlpatterns = [
    path('auth/', include('authentication.urls')),
    path('games/', include('games.urls')),
]
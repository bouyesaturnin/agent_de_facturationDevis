from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'clients', views.ClientViewSet)
router.register(r'chantiers', views.ChantierViewSet)
router.register(r'materiaux', views.MateriauPlomberieViewSet)
router.register(r'devis', views.DevisViewSet)
router.register(r'lignes-devis', views.LigneDevisViewSet)
router.register(r'artisan-profil', views.ArtisanProfileViewSet)


urlpatterns = [
    path('ping/', views.ping),
    path('register/', views.register),
    path('generate-numero/', views.generate_numero),
    path('', include(router.urls)),
]
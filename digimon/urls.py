# digimon/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    DigimonViewSet,
    digimon_by_id_page,
    digimon_by_name_page,
    digimon_create_view,
    digimon_list_page,
    get_digimon_by_id,
    get_digimon_by_name, digimon_update_view,
)

router = DefaultRouter()
router.register(r"digimons", DigimonViewSet, basename="digimon")

urlpatterns = [
    # DRF API Endpoint'leri
    path("", include(router.urls)),
    path("digimons/by-name/<str:name>/", get_digimon_by_name, name="get-digimon-by-name"),
    path("digimons/by-id/<int:pk>/", get_digimon_by_id, name="get-digimon-by-id"),

    # Arayüz Sayfaları
    path("ui/create/", digimon_create_view, name="digimon-create"),
    path("ui/update/<int:pk>", digimon_update_view, name="digimon-update"),
    path("ui/list/", digimon_list_page, name="digimon-list-ui"),
    path("ui/by-name/", digimon_by_name_page, name="digimon-by-name-ui"),
    path("ui/by-id/", digimon_by_id_page, name="digimon-by-id-ui"),
]

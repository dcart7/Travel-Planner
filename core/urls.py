from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, PlaceViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'places', PlaceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
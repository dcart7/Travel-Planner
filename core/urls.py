from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import ProjectViewSet, PlaceViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

# nested: /api/projects/{project_pk}/places/
projects_router = routers.NestedDefaultRouter(router, r'projects', lookup='project')
projects_router.register(r'places', PlaceViewSet, basename='project-places')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(projects_router.urls)),
]
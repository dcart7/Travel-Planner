from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Count, Q

from .models import Project, Place
from .serializers import ProjectSerializer, PlaceSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing projects.
    supports filtering and searching by project name and description.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    
    # as a bonus, adding search and ordering capabilities for projects
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'name']

    def destroy(self, request, *args, **kwargs):
        """
        requirement: A project cannot be deleted if it has any visited places.
        """
        project = self.get_object()
        
        # checkind for visited places 
        if project.places.filter(visited=True).exists():
            return Response(
                {"error": "Cannot delete project with visited places."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        return super().destroy(request, *args, **kwargs)


class PlaceViewSet(viewsets.ModelViewSet):
    """
        API endpoint for managing places.
        supports filtering by project_id to retrieve all places for a specific project.
    """
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer
    
    filter_backends = [filters.OrderingFilter]
    filterset_fields = ['project'] 

    def perform_create(self, serializer):
        """
        maximum of 10 places per project
        """
        project = serializer.validated_data['project']
        if project.places.count() >= 10:
             raise ValidationError("Cannot add more places. Project limit of 10 reached.")
        

        serializer.save()
        

        if project.is_completed:
            project.is_completed = False
            project.save()

    def perform_update(self, serializer):
        """
        Требование: When all places in a project are marked as visited, the project is marked as completed.
        """

        place = serializer.save()
        project = place.project
        

        all_places = project.places.all()
        
        if all_places.exists() and all(p.visited for p in all_places):
            project.is_completed = True
        else:
            project.is_completed = False
            
        project.save()

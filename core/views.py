from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Project, Place
from .serializers import ProjectSerializer, PlaceSerializer, PlaceUpdateSerializer
from .services import validate_and_fetch_artwork

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

        # checking for visited places
        if project.places.filter(visited=True).exists():
            return Response(
                {"error": "Cannot delete project with visited places."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)


class PlaceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing places nested under a project.
    All routes are scoped to /api/projects/{project_pk}/places/
    """
    serializer_class = PlaceSerializer

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return PlaceUpdateSerializer
        return PlaceSerializer

    def get_project(self):
        """Helper: resolve the parent project from URL kwargs."""
        project_pk = self.kwargs.get('project_pk')
        try:
            return Project.objects.get(pk=project_pk)
        except Project.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(f"Project with id {project_pk} not found.")

    def get_queryset(self):
        """requirement: list all places for a specific project"""
        project = self.get_project()
        return Place.objects.filter(project=project)

    def create(self, request, *args, **kwargs):
        """
        requirement: Add a place to an existing project.
        Validates: project limit (max 10), no duplicate artworks, artwork exists in API.
        """
        project = self.get_project()

        # maximum of 10 places per project
        if project.places.count() >= 10:
            return Response(
                {"error": "Cannot add more places. Project limit of 10 reached."},
                status=status.HTTP_400_BAD_REQUEST
            )

        artwork_id = request.data.get('artwork_id')
        if artwork_id is None:
            return Response({"error": "artwork_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # check for duplicate artwork in this project
        if project.places.filter(artwork_id=artwork_id).exists():
            return Response(
                {"error": f"Artwork {artwork_id} is already in this project."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # validate artwork exists in Art Institute API
        artwork_data = validate_and_fetch_artwork(artwork_id)
        if not artwork_data:
            return Response(
                {"error": f"Artwork with ID {artwork_id} does not exist in the Art Institute API."},
                status=status.HTTP_400_BAD_REQUEST
            )

        notes = request.data.get('notes', '')
        place = Place.objects.create(
            project=project,
            artwork_id=artwork_id,
            title=artwork_data['title'],
            image_id=artwork_data.get('image_id'),
            notes=notes,
        )

        serializer = PlaceSerializer(place)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        """
        requirement: When all places in a project are marked as visited, the project is marked as completed.
        """
        place = serializer.save()
        project = place.project

        all_places = project.places.all()

        if all_places.exists() and all(p.visited for p in all_places):
            project.is_completed = True
        else:
            project.is_completed = False

        project.save()

    def destroy(self, request, *args, **kwargs):
        """Deleting a place also re-evaluates project completion status."""
        place = self.get_object()
        project = place.project
        place.delete()

        all_places = project.places.all()
        if all_places.exists() and all(p.visited for p in all_places):
            project.is_completed = True
        else:
            project.is_completed = False
        project.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

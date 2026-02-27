from rest_framework import serializers
from .models import Project, Place
from .services import validate_and_fetch_artwork

class PlaceSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    image_id = serializers.CharField(read_only=True)

    class Meta:
        model = Place
        fields = ['id', 'artwork_id', 'title', 'image_id', 'notes', 'visited']

    def validate_artwork_id(self, value):
        """requirement: check if artwork_id exists in external API and fetch title"""
        artwork_data = validate_and_fetch_artwork(value)
        if not artwork_data:
            raise serializers.ValidationError(f"Artwork with ID {value} does not exist in the Art Institute API.")
        return value

class PlaceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a place — only notes and visited are writable."""
    class Meta:
        model = Place
        fields = ['id', 'artwork_id', 'title', 'image_id', 'notes', 'visited']
        read_only_fields = ['id', 'artwork_id', 'title', 'image_id']

class ProjectSerializer(serializers.ModelSerializer):
    places = PlaceSerializer(many=True, required=False)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'start_date', 'is_completed', 'places']
        read_only_fields = ['is_completed']

    def validate_places(self, value):
        """requirement: A project can have a maximum of 10 places"""
        if value and len(value) > 10:
            raise serializers.ValidationError("A project can have a maximum of 10 places.")

        # checking for duplicates of artworks in the request
        artwork_ids = [place.get('artwork_id') for place in value]
        if len(artwork_ids) != len(set(artwork_ids)):
            raise serializers.ValidationError("Duplicate artwork IDs found in the request.")

        return value

    def create(self, validated_data):
        """requirement: Creating a project and its places in a single request"""
        places_data = validated_data.pop('places', [])
        project = Project.objects.create(**validated_data)

        for place_data in places_data:
            place_data.pop('title', None)
            place_data.pop('image_id', None)

            if 'artwork_id' in place_data:
                artwork_data = validate_and_fetch_artwork(place_data['artwork_id'])
                title = artwork_data['title'] if artwork_data else 'Unknown Title'
                fetched_image_id = artwork_data.get('image_id') if artwork_data else None
                Place.objects.create(project=project, title=title, image_id=fetched_image_id, **place_data)

        return project
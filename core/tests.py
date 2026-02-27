from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Project, Place

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_ARTWORK = {'id': 27992, 'title': 'A Sunday on La Grande Jatte', 'image_id': 'abc123'}
MOCK_ARTWORK_2 = {'id': 111628, 'title': 'American Gothic', 'image_id': 'def456'}


def mock_fetch(artwork_id):
    mapping = {
        27992: MOCK_ARTWORK,
        111628: MOCK_ARTWORK_2,
    }
    return mapping.get(int(artwork_id))


# ---------------------------------------------------------------------------
# Project Tests
# ---------------------------------------------------------------------------

class ProjectCRUDTests(APITestCase):
    """Tests for the /api/projects/ endpoint."""

    def test_create_project_minimal(self):
        """Create a project with only a name."""
        r = self.client.post('/api/projects/', {'name': 'Trip to Chicago'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['name'], 'Trip to Chicago')
        self.assertFalse(r.data['is_completed'])

    def test_create_project_with_all_fields(self):
        """Create a project with name, description and start_date."""
        payload = {'name': 'Euro Trip', 'description': 'Museum tour', 'start_date': '2025-06-01'}
        r = self.client.post('/api/projects/', payload, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['description'], 'Museum tour')
        self.assertEqual(r.data['start_date'], '2025-06-01')

    @patch('core.serializers.validate_and_fetch_artwork', side_effect=mock_fetch)
    def test_create_project_with_places(self, _mock):
        """Create a project with places in one request."""
        payload = {
            'name': 'Art Tour',
            'places': [{'artwork_id': 27992}, {'artwork_id': 111628}]
        }
        r = self.client.post('/api/projects/', payload, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(r.data['places']), 2)
        self.assertEqual(r.data['places'][0]['title'], 'A Sunday on La Grande Jatte')

    @patch('core.serializers.validate_and_fetch_artwork', side_effect=mock_fetch)
    def test_create_project_duplicate_places_rejected(self, _mock):
        """Duplicate artwork IDs in one create request should be rejected."""
        payload = {
            'name': 'Bad Trip',
            'places': [{'artwork_id': 27992}, {'artwork_id': 27992}]
        }
        r = self.client.post('/api/projects/', payload, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('core.serializers.validate_and_fetch_artwork', side_effect=mock_fetch)
    def test_create_project_exceeds_10_places(self, _mock):
        """More than 10 places in one request should be rejected."""
        places = [{'artwork_id': i} for i in range(11)]
        r = self.client.post('/api/projects/', {'name': 'Big Trip', 'places': places}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_projects(self):
        Project.objects.create(name='P1')
        Project.objects.create(name='P2')
        r = self.client.get('/api/projects/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        results = r.data['results'] if isinstance(r.data, dict) else r.data
        self.assertGreaterEqual(len(results), 2)

    def test_retrieve_project(self):
        project = Project.objects.create(name='Single')
        r = self.client.get(f'/api/projects/{project.pk}/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['name'], 'Single')

    def test_update_project(self):
        project = Project.objects.create(name='Old Name')
        r = self.client.patch(f'/api/projects/{project.pk}/', {'name': 'New Name'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['name'], 'New Name')

    def test_delete_project_no_visited_places(self):
        project = Project.objects.create(name='Delete Me')
        r = self.client.delete(f'/api/projects/{project.pk}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_project_with_visited_place_rejected(self):
        """requirement: projects with visited places cannot be deleted."""
        project = Project.objects.create(name='Keep Me')
        Place.objects.create(project=project, artwork_id=1, title='Art', visited=True)
        r = self.client.delete(f'/api/projects/{project.pk}/')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_projects(self):
        Project.objects.create(name='Paris Trip', description='Eiffel tower')
        Project.objects.create(name='Rome Trip', description='Colosseum')
        r = self.client.get('/api/projects/?search=Paris')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        results = r.data['results'] if isinstance(r.data, dict) else r.data
        self.assertEqual(len(results), 1)

    def test_retrieve_nonexistent_project(self):
        r = self.client.get('/api/projects/9999/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Place Tests
# ---------------------------------------------------------------------------

class PlaceCRUDTests(APITestCase):
    """Tests for /api/projects/{project_pk}/places/"""

    def setUp(self):
        self.project = Project.objects.create(name='My Trips')

    def places_url(self, pk=None):
        base = f'/api/projects/{self.project.pk}/places/'
        return f'{base}{pk}/' if pk else base

    @patch('core.views.validate_and_fetch_artwork', side_effect=mock_fetch)
    def test_add_place_to_project(self, _mock):
        r = self.client.post(self.places_url(), {'artwork_id': 27992}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['artwork_id'], 27992)
        self.assertEqual(r.data['title'], 'A Sunday on La Grande Jatte')

    @patch('core.views.validate_and_fetch_artwork', return_value=None)
    def test_add_place_invalid_artwork_rejected(self, _mock):
        """Artwork not found in Art Institute API should be rejected."""
        r = self.client.post(self.places_url(), {'artwork_id': 99999999}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('core.views.validate_and_fetch_artwork', side_effect=mock_fetch)
    def test_add_duplicate_place_rejected(self, _mock):
        """requirement: same artwork cannot be added twice to same project."""
        Place.objects.create(project=self.project, artwork_id=27992, title='Art')
        r = self.client.post(self.places_url(), {'artwork_id': 27992}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('core.views.validate_and_fetch_artwork', side_effect=mock_fetch)
    def test_project_limit_10_places(self, _mock):
        """requirement: max 10 places per project."""
        for i in range(10):
            Place.objects.create(project=self.project, artwork_id=i, title=f'Art {i}')
        r = self.client.post(self.places_url(), {'artwork_id': 27992}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_places_for_project(self):
        Place.objects.create(project=self.project, artwork_id=1, title='One')
        Place.objects.create(project=self.project, artwork_id=2, title='Two')
        r = self.client.get(self.places_url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        results = r.data['results'] if isinstance(r.data, dict) else r.data
        self.assertEqual(len(results), 2)

    def test_list_places_scoped_to_project(self):
        """Places from another project must not appear in this project's list."""
        other = Project.objects.create(name='Other')
        Place.objects.create(project=other, artwork_id=999, title='Foreign')
        Place.objects.create(project=self.project, artwork_id=1, title='Mine')
        r = self.client.get(self.places_url())
        results = r.data['results'] if isinstance(r.data, dict) else r.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['artwork_id'], 1)

    def test_retrieve_single_place(self):
        place = Place.objects.create(project=self.project, artwork_id=1, title='Solo')
        r = self.client.get(self.places_url(place.pk))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['title'], 'Solo')

    def test_update_place_notes(self):
        place = Place.objects.create(project=self.project, artwork_id=1, title='Art')
        r = self.client.patch(self.places_url(place.pk), {'notes': 'Beautiful!'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['notes'], 'Beautiful!')

    def test_update_place_artwork_id_is_ignored(self):
        """artwork_id should be read-only on update."""
        place = Place.objects.create(project=self.project, artwork_id=1, title='Art')
        r = self.client.patch(self.places_url(place.pk), {'artwork_id': 999}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        place.refresh_from_db()
        self.assertEqual(place.artwork_id, 1)  # unchanged

    def test_mark_place_as_visited(self):
        place = Place.objects.create(project=self.project, artwork_id=1, title='Art')
        r = self.client.patch(self.places_url(place.pk), {'visited': True}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data['visited'])

    def test_project_completed_when_all_places_visited(self):
        """requirement: project is marked completed when all places visited."""
        p1 = Place.objects.create(project=self.project, artwork_id=1, title='Art 1')
        p2 = Place.objects.create(project=self.project, artwork_id=2, title='Art 2')
        self.client.patch(self.places_url(p1.pk), {'visited': True}, format='json')
        self.client.patch(self.places_url(p2.pk), {'visited': True}, format='json')
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_completed)

    def test_project_not_completed_if_some_unvisited(self):
        p1 = Place.objects.create(project=self.project, artwork_id=1, title='Art 1')
        Place.objects.create(project=self.project, artwork_id=2, title='Art 2')
        self.client.patch(self.places_url(p1.pk), {'visited': True}, format='json')
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_completed)

    def test_add_place_to_nonexistent_project(self):
        r = self.client.post('/api/projects/9999/places/', {'artwork_id': 27992}, format='json')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_place_missing_artwork_id(self):
        r = self.client.post(self.places_url(), {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

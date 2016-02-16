

import json
import pytest
import fitter_api

from datetime import datetime


class TestFitterApi:
    def setup_class(self):
        """Setup the test class."""
        self.app = fitter_api.app
        self.app.config['TESTING'] = True
        self.app.config['AUTH_TESTING'] = True
        self.client = self.app.test_client()

    def setup_method(self, method):
        """Setup for each method."""
        with self.app.app_context():
            fitter_api.db.create_all()

            populate_test_data()

    def teardown_method(self, method):
        """Teardown after each method."""
        with self.app.app_context():
            fitter_api.db.drop_all()

    def test_character_details(self):
        """Test getting a characters details."""
        response = self.client.get('/characters/1/')

        assert response.status_code == 200
        assert json.loads(response.data) == {
            'id': 1,
            'name': 'Test Character',
            'liked': 10,
            'passed': 5,
        }

    def test_character_details_404(self):
        """Ensure we 404 if the character is not found."""
        response = self.client.get('/characters/99999/')

        assert response.status_code == 404

    def test_character_history(self):
        """Test getting a characters history of fit descisions."""
        test_character_fit = fitter_api.CharacterFitModel(9, 1, True)

        fitter_api.db.session.add(test_character_fit)

        response = self.client.get('/characters/1/fits/')

        assert response.status_code == 200
        assert json.loads(response.data) == {
            'id': 1,
            'fits': [
                {'id': 9, 'liked': True},
            ],
        }

    def test_get_new_fit(self):
        """Test we get a new fit that the character has not used yet."""
        self.app.config['TEST_TOKEN_DATA'] = {'character_id': 1}
        fit_item_one = fitter_api.FitItemModel(9, 555, 89, 5)
        fit_item_two = fitter_api.FitItemModel(8, 555, 89, 5)
        character_fit = fitter_api.CharacterFitModel(8, 1, True)
        
        fitter_api.db.session.add(fit_item_one)
        fitter_api.db.session.add(fit_item_two)
        fitter_api.db.session.add(character_fit)
        
        # TODO: Mock out random.choice and ensure it is called with just
        # fit_item_one to rule out a test passing/failing based on random.
        
        response = self.client.get('/characters/1/newfit/')

        assert response.status_code == 200
        assert json.loads(response.data) == {
            'id': 9,
            'items': [
                {'id': 555, 'flag': 89, 'quantity': 5},
            ],
        }

    def test_set_fit_status(self):
        """Test we can correctly set a fits status for a character."""
        self.app.config['TEST_TOKEN_DATA'] = {'character_id': 1}
        
        test_character_fit = fitter_api.CharacterFitModel(9, 1, False)
        fitter_api.db.session.add(test_character_fit)

        response = self.client.put('/characters/1/fits/9/', data={'liked': True})

        assert response.status_code == 200
        assert json.loads(response.data) == {
            'id': 9,
            'liked': True,
        }

    def test_set_fit_status_on_creation(self):
        """Test 201 if the status of the fit is set for the first time."""
        self.app.config['TEST_TOKEN_DATA'] = {'character_id': 1}
        response = self.client.put('/characters/1/fits/9/', data={'liked': True})

        assert response.status_code == 201
        assert json.loads(response.data) == {
            'id': 9,
            'liked': True,
        }

    def test_set_fit_status_on_nonexistent_fit(self):
        """Test we 404 if the fit specified doesn't exist in our DB."""
        self.app.config['TEST_TOKEN_DATA'] = {'character_id': 1}
        response = self.client.put( '/characters/1/fits/5/', data={'liked': True})

        assert response.status_code == 404

    def test_set_fit_with_no_data(self):
        """Test 404 if no data passed in the PUT for setting a fits status."""
        self.app.config['TEST_TOKEN_DATA'] = {'character_id': 1}
        response = self.client.put('/characters/1/fits/999/')

        assert response.status_code == 400
    
    def test_set_fit_status_nonexistent_character(self):
        """Test 404 if the specified character doesn't exist in our DB."""
        self.app.config['TEST_TOKEN_DATA'] = {'character_id': 2}
        
        response = self.client.put('/characters/2/fits/9/', data={'liked': True})

        assert response.status_code == 404
    
    def test_character_post(self):
        """Test adding new characters."""
        self.app.config['TEST_TOKEN_DATA'] = {
            'character_id': 2,
            'character_name': 'Test',
        }
        
        response  = self.client.post('/characters/')
        
        assert response.status_code == 201
        assert response.headers['Location'] == 'http://localhost/characters/2/'
    
    def test_character_post_existing_character(self):
        """Test adding a character that already exists."""
        self.app.config['TEST_TOKEN_DATA'] = {
            'character_id': 1,
            'character_name': 'Test',
        }
        
        response  = self.client.post('/characters/')
        
        assert response.status_code == 409

def populate_test_data():
    test_character = fitter_api.CharacterDetailsModel(1, 'Test Character')
    test_character.liked = 10
    test_character.passed = 5

    test_fit = fitter_api.FitModel(9, datetime.now())

    fitter_api.db.session.add(test_character)
    fitter_api.db.session.add(test_fit)
    fitter_api.db.session.commit()

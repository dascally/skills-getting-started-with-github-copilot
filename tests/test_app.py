"""
Test suite for Mergington High School API
Tests all endpoints including activities listing, signup, and unregister functionality
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        if name in activities:
            activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_html(self, client):
        """Test that root path redirects to static HTML page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that activities endpoint returns successful response"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_json(self, client):
        """Test that activities endpoint returns JSON data"""
        response = client.get("/activities")
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_contains_expected_fields(self, client):
        """Test that each activity contains required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
    
    def test_get_activities_includes_all_activities(self, client):
        """Test that all expected activities are returned"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = [
            "Chess Club", "Programming Class", "Gym Class",
            "Soccer Team", "Basketball Club", "Art Club",
            "Choir", "Debate Team", "Science Club"
        ]
        
        for activity in expected_activities:
            assert activity in data


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client, reset_activities):
        """Test that signup actually adds participant to the activity"""
        email = "newstudent@mergington.edu"
        activity = "Chess Club"
        
        # Get initial participants
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity]["participants"]
        
        # Sign up
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Verify participant was added
        after_response = client.get("/activities")
        after_participants = after_response.json()[activity]["participants"]
        
        assert email not in initial_participants
        assert email in after_participants
        assert len(after_participants) == len(initial_participants) + 1
    
    def test_signup_for_nonexistent_activity(self, client, reset_activities):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test that signing up twice with same email returns error"""
        email = "duplicate@mergington.edu"
        activity = "Chess Club"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_email(self, client, reset_activities):
        """Test signup with special characters in email"""
        # Use a dot in the email which is common and safe in URLs
        email = "test.user@mergington.edu"
        activity = "Programming Class"
        
        response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify it was added correctly
        after_response = client.get("/activities")
        participants = after_response.json()[activity]["participants"]
        assert email in participants


class TestUnregisterEndpoint:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        # First sign up a participant
        email = "unregister@mergington.edu"
        activity = "Chess Club"
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes participant from activity"""
        email = "remove@mergington.edu"
        activity = "Science Club"
        
        # Sign up
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Verify participant is there
        before_response = client.get("/activities")
        before_participants = before_response.json()[activity]["participants"]
        assert email in before_participants
        
        # Unregister
        client.delete(f"/activities/{activity}/unregister?email={email}")
        
        # Verify participant was removed
        after_response = client.get("/activities")
        after_participants = after_response.json()[activity]["participants"]
        assert email not in after_participants
        assert len(after_participants) == len(before_participants) - 1
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_participant_not_signed_up(self, client, reset_activities):
        """Test unregister for a participant who isn't signed up"""
        email = "notsignedup@mergington.edu"
        activity = "Chess Club"
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregister for a participant who was already in the activity"""
        # Use an existing participant from the initial data
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Verify participant exists
        before_response = client.get("/activities")
        before_participants = before_response.json()[activity]["participants"]
        assert email in before_participants
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify removal
        after_response = client.get("/activities")
        after_participants = after_response.json()[activity]["participants"]
        assert email not in after_participants


class TestEndToEndScenarios:
    """End-to-end test scenarios"""
    
    def test_complete_signup_and_unregister_flow(self, client, reset_activities):
        """Test complete flow of signing up and then unregistering"""
        email = "e2e@mergington.edu"
        activity = "Debate Team"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities")
        after_signup_count = len(after_signup.json()[activity]["participants"])
        assert after_signup_count == initial_count + 1
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregister
        after_unregister = client.get("/activities")
        after_unregister_count = len(after_unregister.json()[activity]["participants"])
        assert after_unregister_count == initial_count
    
    def test_multiple_participants_same_activity(self, client, reset_activities):
        """Test multiple participants signing up for the same activity"""
        activity = "Art Club"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        # Get initial count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Sign up all students
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all were added
        final_response = client.get("/activities")
        final_participants = final_response.json()[activity]["participants"]
        assert len(final_participants) == initial_count + len(emails)
        
        for email in emails:
            assert email in final_participants
    
    def test_participant_signs_up_for_multiple_activities(self, client, reset_activities):
        """Test same participant signing up for multiple activities"""
        email = "multisport@mergington.edu"
        activities_list = ["Soccer Team", "Basketball Club", "Gym Class"]
        
        # Sign up for all activities
        for activity in activities_list:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify participant is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities_list:
            assert email in all_activities[activity]["participants"]

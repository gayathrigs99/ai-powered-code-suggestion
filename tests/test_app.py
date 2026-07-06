import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


@pytest.fixture
def fresh_app():
    """Fixture to reset activities before each test"""
    # Reset activities to known state
    from app import activities
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": []
        }
    })
    yield
    # Cleanup after test
    activities.clear()


class TestGetActivities:
    def test_get_all_activities(self, fresh_app):
        """Test fetching all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activities_contain_required_fields(self, fresh_app):
        """Test that activities have all required fields"""
        response = client.get("/activities")
        data = response.json()
        chess = data["Chess Club"]
        
        assert "description" in chess
        assert "schedule" in chess
        assert "max_participants" in chess
        assert "participants" in chess
        assert isinstance(chess["participants"], list)
    
    def test_activities_have_correct_participant_count(self, fresh_app):
        """Test that participant lists are correct"""
        response = client.get("/activities")
        data = response.json()
        
        assert len(data["Chess Club"]["participants"]) == 2
        assert len(data["Programming Class"]["participants"]) == 1
        assert len(data["Gym Class"]["participants"]) == 0


class TestSignup:
    def test_signup_new_participant(self, fresh_app):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]
    
    def test_participant_added_to_list(self, fresh_app):
        """Test that signed up participant appears in activity"""
        client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")
        
        response = client.get("/activities")
        data = response.json()
        participants = data["Chess Club"]["participants"]
        
        assert "newstudent@mergington.edu" in participants
        assert len(participants) == 3  # 2 original + 1 new
    
    def test_signup_nonexistent_activity(self, fresh_app):
        """Test signing up for activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_participant(self, fresh_app):
        """Test that duplicate signups are rejected"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_multiple_activities(self, fresh_app):
        """Test that a student can sign up for multiple activities"""
        student_email = "versatile@mergington.edu"
        
        response1 = client.post(
            f"/activities/Chess Club/signup?email={student_email}"
        )
        response2 = client.post(
            f"/activities/Programming Class/signup?email={student_email}"
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        activities_response = client.get("/activities")
        data = activities_response.json()
        
        assert student_email in data["Chess Club"]["participants"]
        assert student_email in data["Programming Class"]["participants"]


class TestUnregister:
    def test_unregister_existing_participant(self, fresh_app):
        """Test removing a participant from activity"""
        response = client.delete(
            "/activities/Chess Club/participants?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "michael@mergington.edu" in data["message"]
    
    def test_participant_removed_from_list(self, fresh_app):
        """Test that unregistered participant is removed"""
        client.delete(
            "/activities/Chess Club/participants?email=michael@mergington.edu"
        )
        
        response = client.get("/activities")
        data = response.json()
        participants = data["Chess Club"]["participants"]
        
        assert "michael@mergington.edu" not in participants
        assert len(participants) == 1  # 2 original - 1 removed
    
    def test_unregister_nonexistent_activity(self, fresh_app):
        """Test removing from activity that doesn't exist"""
        response = client.delete(
            "/activities/Fake Club/participants?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_nonexistent_participant(self, fresh_app):
        """Test removing participant who isn't signed up"""
        response = client.delete(
            "/activities/Chess Club/participants?email=notreal@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Participant not found" in data["detail"]
    
    def test_unregister_then_signup_again(self, fresh_app):
        """Test that unregistered participant can sign up again"""
        email = "michael@mergington.edu"
        
        # First unregister
        client.delete(f"/activities/Chess Club/participants?email={email}")
        
        # Then sign up again
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 200
        
        # Verify they're signed up
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email in data["Chess Club"]["participants"]


class TestIntegration:
    def test_full_signup_workflow(self, fresh_app):
        """Test complete signup workflow"""
        email = "integration_test@mergington.edu"
        activity = "Programming Class"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email in data[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/participants?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email not in data[activity]["participants"]
    
    def test_availability_updates_correctly(self, fresh_app):
        """Test that availability spots decrease on signup"""
        response1 = client.get("/activities")
        data1 = response1.json()
        gym_initial = data1["Gym Class"]["max_participants"] - len(data1["Gym Class"]["participants"])
        
        # Sign up a new participant
        client.post("/activities/Gym Class/signup?email=newcomer@mergington.edu")
        
        response2 = client.get("/activities")
        data2 = response2.json()
        gym_after = data2["Gym Class"]["max_participants"] - len(data2["Gym Class"]["participants"])
        
        assert gym_after == gym_initial - 1

import requests
import sys
import json
from datetime import datetime

class CasaLimpiaAPITester:
    def __init__(self, base_url="https://casa-limpia.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.current_week_data = None

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out after {timeout} seconds")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_generate_schedules(self):
        """Test schedule generation"""
        success, response = self.run_test(
            "Generate Schedules",
            "POST",
            "generate-schedules",
            200
        )
        return success

    def test_get_current_week(self):
        """Test getting current week schedule"""
        success, response = self.run_test(
            "Get Current Week",
            "GET",
            "current-week",
            200
        )
        if success:
            self.current_week_data = response
            # Validate the response structure for individual tasks
            required_fields = ['week_start', 'week_end', 'joan_area', 'mery_area', 'paco_area', 'belen_area', 'tasks']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Check if tasks exist and we have 4 individual tasks
            if not response.get('tasks') or len(response['tasks']) != 4:
                print(f"❌ Expected 4 individual tasks, found {len(response.get('tasks', []))}")
                return False
                
            # Validate each person has a task
            persons = ['joan', 'mery', 'paco', 'belen']
            found_persons = [task['person'] for task in response['tasks']]
            for person in persons:
                if person not in found_persons:
                    print(f"❌ Missing task for person: {person}")
                    return False
                    
            print(f"   Week: {response['week_start']} to {response['week_end']}")
            print(f"   Joan: {response['joan_area']}")
            print(f"   Mery: {response['mery_area']}")
            print(f"   Paco: {response['paco_area']}")
            print(f"   Belén: {response['belen_area']}")
            print(f"   Total individual tasks: {len(response['tasks'])}")
            
        return success

    def test_complete_task(self):
        """Test marking individual person tasks as completed"""
        if not self.current_week_data:
            print("❌ Cannot test task completion - no current week data")
            return False
            
        # Test completing Joan's task
        joan_task_data = {
            "week_start": self.current_week_data['week_start'],
            "person": "joan",
            "completed": True
        }
        
        success1, response1 = self.run_test(
            "Complete Joan's Task",
            "POST",
            "complete-task",
            200,
            data=joan_task_data
        )
        
        # Test completing Paco's task
        paco_task_data = {
            "week_start": self.current_week_data['week_start'],
            "person": "paco",
            "completed": True
        }
        
        success2, response2 = self.run_test(
            "Complete Paco's Task",
            "POST",
            "complete-task",
            200,
            data=paco_task_data
        )
        
        # Test uncompleting Joan's task
        joan_task_data['completed'] = False
        success3, response3 = self.run_test(
            "Uncomplete Joan's Task",
            "POST",
            "complete-task",
            200,
            data=joan_task_data
        )
        
        return success1 and success2 and success3

    def test_get_all_schedules(self):
        """Test getting all schedules (debugging endpoint)"""
        success, response = self.run_test(
            "Get All Schedules",
            "GET",
            "schedules",
            200,
            timeout=15  # Longer timeout for potentially large response
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} total schedules")
        return success

    def test_invalid_endpoints(self):
        """Test invalid endpoints return proper errors"""
        print(f"\n🔍 Testing Invalid Endpoints...")
        
        # Test non-existent endpoint
        success1, _ = self.run_test(
            "Non-existent Endpoint",
            "GET",
            "non-existent",
            404
        )
        
        # Test invalid task completion data
        invalid_data = {
            "week_start": "invalid-date",
            "person": "invalid_person",
            "completed": True
        }
        
        success2, _ = self.run_test(
            "Invalid Person Data",
            "POST",
            "complete-task",
            422,  # Validation error
            data=invalid_data
        )
        
        return success1 and success2

def main():
    print("🏠 Casa Limpia API Testing Suite")
    print("=" * 50)
    
    tester = CasaLimpiaAPITester()
    
    # Run all tests
    tests = [
        tester.test_root_endpoint,
        tester.test_generate_schedules,
        tester.test_get_current_week,
        tester.test_complete_task,
        tester.test_get_all_schedules,
        tester.test_invalid_endpoints
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
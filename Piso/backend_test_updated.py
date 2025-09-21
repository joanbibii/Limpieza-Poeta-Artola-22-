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
        """Test getting current week schedule with bathroom system"""
        success, response = self.run_test(
            "Get Current Week",
            "GET",
            "current-week",
            200
        )
        if success:
            self.current_week_data = response
            # Validate the response structure for bathroom system
            required_fields = ['week_start', 'week_end', 'joan_area', 'mery_area', 'paco_area', 'belen_area', 
                             'joan_bano', 'mery_bano', 'paco_bano', 'belen_bano', 'tasks']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Check bathroom assignments
            print(f"   Week: {response['week_start']} to {response['week_end']}")
            print(f"   Joan: {response['joan_area']} + Baño: {response['joan_bano']}")
            print(f"   Mery: {response['mery_area']} + Baño: {response['mery_bano']}")
            print(f"   Paco: {response['paco_area']} + Baño: {response['paco_bano']}")
            print(f"   Belén: {response['belen_area']} + Baño: {response['belen_bano']}")
            
            # Validate bathroom alternation logic
            if response['joan_bano'] == response['mery_bano']:
                print(f"❌ Joan and Mery both have same bathroom assignment: {response['joan_bano']}")
                return False
            
            if response['paco_bano'] == response['belen_bano']:
                print(f"❌ Paco and Belén both have same bathroom assignment: {response['paco_bano']}")
                return False
            
            # Check tasks structure - should have 6 tasks (4 main + 2 bathroom)
            tasks = response.get('tasks', [])
            expected_task_count = 6  # 4 main tasks + 2 bathroom tasks
            if len(tasks) != expected_task_count:
                print(f"❌ Expected {expected_task_count} tasks, found {len(tasks)}")
                return False
            
            # Validate task structure
            main_tasks = [t for t in tasks if t['task_type'] == 'limpieza_principal']
            bathroom_tasks = [t for t in tasks if t['task_type'] == 'limpieza_bano']
            
            if len(main_tasks) != 4:
                print(f"❌ Expected 4 main tasks, found {len(main_tasks)}")
                return False
                
            if len(bathroom_tasks) != 2:
                print(f"❌ Expected 2 bathroom tasks, found {len(bathroom_tasks)}")
                return False
            
            # Validate specific person task assignments
            joan_tasks = [t for t in tasks if t['person'] == 'joan']
            mery_tasks = [t for t in tasks if t['person'] == 'mery']
            paco_tasks = [t for t in tasks if t['person'] == 'paco']
            belen_tasks = [t for t in tasks if t['person'] == 'belen']
            
            # Joan should have 2 tasks if joan_bano is True, 1 if False
            expected_joan_tasks = 2 if response['joan_bano'] else 1
            if len(joan_tasks) != expected_joan_tasks:
                print(f"❌ Joan should have {expected_joan_tasks} tasks, found {len(joan_tasks)}")
                return False
            
            # Mery should have 2 tasks if mery_bano is True, 1 if False
            expected_mery_tasks = 2 if response['mery_bano'] else 1
            if len(mery_tasks) != expected_mery_tasks:
                print(f"❌ Mery should have {expected_mery_tasks} tasks, found {len(mery_tasks)}")
                return False
            
            # Paco should have 2 tasks if paco_bano is True, 1 if False
            expected_paco_tasks = 2 if response['paco_bano'] else 1
            if len(paco_tasks) != expected_paco_tasks:
                print(f"❌ Paco should have {expected_paco_tasks} tasks, found {len(paco_tasks)}")
                return False
            
            # Belén should have 2 tasks if belen_bano is True, 1 if False
            expected_belen_tasks = 2 if response['belen_bano'] else 1
            if len(belen_tasks) != expected_belen_tasks:
                print(f"❌ Belén should have {expected_belen_tasks} tasks, found {len(belen_tasks)}")
                return False
            
            print(f"✅ Task distribution correct:")
            print(f"   Joan: {len(joan_tasks)} tasks")
            print(f"   Mery: {len(mery_tasks)} tasks")
            print(f"   Paco: {len(paco_tasks)} tasks")
            print(f"   Belén: {len(belen_tasks)} tasks")
            
        return success

    def test_complete_task_with_bathrooms(self):
        """Test marking tasks as completed with new bathroom system"""
        if not self.current_week_data:
            print("❌ Cannot test task completion - no current week data")
            return False
        
        tasks = self.current_week_data.get('tasks', [])
        success_count = 0
        total_tests = 0
        
        # Test completing Joan's main task
        joan_main_task = next((t for t in tasks if t['person'] == 'joan' and t['task_type'] == 'limpieza_principal'), None)
        if joan_main_task:
            total_tests += 1
            task_data = {
                "week_start": self.current_week_data['week_start'],
                "person": "joan",
                "area": joan_main_task['area'],
                "task_type": "limpieza_principal",
                "completed": True
            }
            
            success, response = self.run_test(
                "Complete Joan's Main Task",
                "POST",
                "complete-task",
                200,
                data=task_data
            )
            if success:
                success_count += 1
        
        # Test completing Joan's bathroom task if exists
        joan_bathroom_task = next((t for t in tasks if t['person'] == 'joan' and t['task_type'] == 'limpieza_bano'), None)
        if joan_bathroom_task:
            total_tests += 1
            task_data = {
                "week_start": self.current_week_data['week_start'],
                "person": "joan",
                "area": joan_bathroom_task['area'],
                "task_type": "limpieza_bano",
                "completed": True
            }
            
            success, response = self.run_test(
                "Complete Joan's Bathroom Task",
                "POST",
                "complete-task",
                200,
                data=task_data
            )
            if success:
                success_count += 1
        
        # Test completing Paco's main task
        paco_main_task = next((t for t in tasks if t['person'] == 'paco' and t['task_type'] == 'limpieza_principal'), None)
        if paco_main_task:
            total_tests += 1
            task_data = {
                "week_start": self.current_week_data['week_start'],
                "person": "paco",
                "area": paco_main_task['area'],
                "task_type": "limpieza_principal",
                "completed": True
            }
            
            success, response = self.run_test(
                "Complete Paco's Main Task",
                "POST",
                "complete-task",
                200,
                data=task_data
            )
            if success:
                success_count += 1
        
        return success_count == total_tests

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
            "area": "invalid_area",
            "task_type": "invalid_task_type",
            "completed": True
        }
        
        success2, _ = self.run_test(
            "Invalid Task Data",
            "POST",
            "complete-task",
            422,  # Validation error
            data=invalid_data
        )
        
        return success1 and success2

def main():
    print("🏠 Casa Limpia API Testing Suite - WITH BATHROOMS")
    print("=" * 60)
    
    tester = CasaLimpiaAPITester()
    
    # Run all tests
    tests = [
        tester.test_root_endpoint,
        tester.test_generate_schedules,
        tester.test_get_current_week,
        tester.test_complete_task_with_bathrooms,
        tester.test_invalid_endpoints
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
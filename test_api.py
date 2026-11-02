
import requests

url = "http://127.0.0.1:5000/api/jobs"

job_data = {
    "recruiter_id": 6,
    "title": "Python Developer Intern",
    "company": "HireLens Technologies",
    "location": "Chandigarh",
    "required_skills": [
        "Python",
        "SQL",
        "Machine Learning",
        "Pandas"
    ],
    "description": "Looking for a Python developer intern.",
    "status": "Published"
}

try:
    response = requests.post(url, json=job_data)

    print("Status Code:", response.status_code)
    print("Response:", response.json())

except requests.exceptions.RequestException as error:
    print("Connection Error:", error)

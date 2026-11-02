import requests

url = "http://127.0.0.1:5000/api/jobs/1"

job_data = {
    "recruiter_id": 6,
    "title": "Python Developer Intern - Updated",
    "company": "HireLens Technologies",
    "location": "Chandigarh",
    "required_skills": [
        "Python",
        "SQL",
        "Flask",
        "Machine Learning"
    ],
    "description": "Updated job description for Python developer intern.",
    "status": "Published"
}

response = requests.put(url, json=job_data)

print("Status Code:", response.status_code)
print("Response:", response.json())
import requests

url = "http://127.0.0.1:5000/api/jobs/1/status"

data = {
    "recruiter_id": 6,
    "status": "Closed"
}

response = requests.patch(url, json=data)

print("Status Code:", response.status_code)
print("Response:", response.json())
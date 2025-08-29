import requests

token = "3|DjhQQEsW9uomW4SiGHlCCYkzRovIwldVizyHHC7u53ae5416"

# Headers with Authorization
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Payload
data = {
    "ticket_id": 1035,
    "status": 51,
}

# Send PUT request with headers
response = requests.put(f'http://127.0.0.1:3000/api/ticket/change-ticket-status',
    json=data,
    headers=headers
)

# Print the response
print(response.json()

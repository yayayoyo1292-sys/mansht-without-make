import requests

USER_TOKEN = "EAATEGfMOkHEBRuUdsy3BuLKt0JLEgbGlY65zDsJZAiSW2ic8nzSsZBtrx5vBJEQY9vyZCLCoda2gWBkq2pIm16S9QxbPhnfLIIvPDAFCtrmu5PS3FbbEDnYsbJYtfOHLSXLj85WZBUZCFHfLBFUxPn9RkHk6nJZCPDv9fHjIepposE5w9FeuZAPzMYoLzK3vsHdthZCSaiiVuh7lZCobqRFQUPnrZAZBnDwwzOepjof3rW5uhCLZCAmR7LQZBZBvIkgsKicW6xelMMnVG9owuWNjbgLmDNCzUJwfzCj0i6xAZDZD"

response = requests.get(
    "https://graph.facebook.com/v19.0/me/accounts",
    params={"access_token": USER_TOKEN}
).json()

print(response)

for page in response.get("data", []):
    print(page["name"], page["id"])
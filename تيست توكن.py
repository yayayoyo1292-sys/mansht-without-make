import requests

PAGE_TOKEN = "EAATEGfMOkHEBRgMFgQnP7lg2unYB6TXFpTrGeCxejvvhxUDPZAZAG9Y0iMranVZAX16ofKBMLzrlvx4pYVs9w51mYGZCQhZC7jwkS1A2ELDGVcw5WwK5stTv7JAPl1VhEGNZB083TxZBvwWlgaNueoBb4sLWVP9tVJE674KmyCubXOEovgDeuas9NZBoWTfMQxHnUBHDMyHRkjT6RpX49kv7TIL4rZBV7ZC69XqDRLcjO4XSQ5R8rbiir50wZDZD"

r = requests.get(
    "https://graph.facebook.com/v19.0/101494423041533",
    params={"fields": "instagram_business_account", "access_token": PAGE_TOKEN}
).json()

print(r)
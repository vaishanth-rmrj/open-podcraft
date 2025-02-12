import os

# prompt the user for the API key
api_key = input("Enter your API key: ")

# Write the API key to the .env file
with open(".env", "w") as file:
    file.write(f"OPENROUTER_API_KEY={api_key}\n")

print("API key has been set and is ready to use.")
import os
import sys
import requests
from msal import ConfidentialClientApplication

# Configuration
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
TENANT_ID = os.getenv('AZURE_TENANT_ID')
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_access_token():
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in result:
        return result["access_token"]
    else:
        print(f"Error getting token: {result.get('error')}")
        print(result.get('error_description'))
        sys.exit(1)

def get_user_id(email, headers):
    url = f"https://graph.microsoft.com/v1.0/users/{email}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('id')
    else:
        print(f"Error finding user {email}: {response.text}")
        return None

def get_role_id(role_name, headers):
    # Note: This lists directory roles. Some roles might need to be activated first.
    url = "https://graph.microsoft.com/v1.0/directoryRoles"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        roles = response.json().get('value', [])
        for role in roles:
            if role.get('displayName') == role_name:
                return role.get('id')
        
        # If role not found in active list, check directoryRoleTemplates and activate it? 
        # For simplicity, we assume the role is already instantiated in the directory.
        print(f"Role '{role_name}' not found. Ensure it is activated in the tenant.")
        return None
    else:
        print(f"Error listing roles: {response.text}")
        return None

def assign_role(user_id, role_id, headers):
    url = f"https://graph.microsoft.com/v1.0/directoryRoles/{role_id}/members/$ref"
    data = {
        "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"
    }
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 204:
        print("Role assigned successfully.")
    else:
        print(f"Error assigning role: {response.text}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python manage_o365_role.py <user_email> <role_name>")
        print("Example: python manage_o365_role.py user@example.com 'Global Administrator'")
        sys.exit(1)

    user_email = sys.argv[1]
    role_name = sys.argv[2]

    if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID]):
        print("Error: Please set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID environment variables.")
        sys.exit(1)

    print("Getting access token...")
    token = get_access_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    print(f"Looking up user: {user_email}...")
    user_id = get_user_id(user_email, headers)
    if not user_id:
        sys.exit(1)

    print(f"Looking up role: {role_name}...")
    role_id = get_role_id(role_name, headers)
    if not role_id:
        sys.exit(1)

    print(f"Assigning role '{role_name}' to user '{user_email}'...")
    assign_role(user_id, role_id, headers)

if __name__ == "__main__":
    main()

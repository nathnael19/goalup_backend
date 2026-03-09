"""
Script to create an admin user for the GoalUp backend.
Run this script to create the initial admin user.
"""
import sys
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def create_admin_user(email: str, password: str, full_name: str):
    """Create an admin user in Supabase."""
    load_dotenv()
    
    supabase_url = os.environ.get("SUPABASE_PROJECT_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_PROJECT_URL and SUPABASE_SERVICE_ROLE_KEY must be configured in .env")
        return

    # Initialize Supabase Admin Client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        # Check if user already exists
        response = supabase.table('users').select('*').eq('email', email).execute()
        
        if len(response.data) > 0:
            print(f"User with email {email} already exists!")
            existing_user = response.data[0]
            if not existing_user.get('is_superuser'):
                print("Upgrading existing user to SUPER_ADMIN...")
                supabase.table('users').update({
                    'is_superuser': True,
                    'role': 'SUPER_ADMIN'
                }).eq('id', existing_user['id']).execute()
                print("✅ User upgraded successfully!")
            return
        
        # Create new admin user in Auth
        print("Creating new user in Supabase Auth...")
        user_response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name
            }
        })
        
        user_id = user_response.user.id
        
        # Explicitly upsert the user into public.users table to ensure sync exists
        print("Ensuring user profile exists in public.users...")
        supabase.table('users').upsert({
            'id': user_id,
            'email': email,
            'full_name': full_name,
            'is_active': True,
            'is_superuser': True,
            'role': 'SUPER_ADMIN'
        }).execute()
        
        print(f"✅ Admin user created and synced successfully!")
        print(f"   Email: {email}")
        print(f"   Name: {full_name}")
        print(f"   ID: {user_id}")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")

import getpass

if __name__ == "__main__":
    print("\n--- Create GoalUp Admin User ---")
    email = input("Email: ").strip()
    full_name = input("Full Name: ").strip()
    password = getpass.getpass("Password: ")
    
    if not email or not full_name or not password:
        print("Error: All fields are required.")
        sys.exit(1)
        
    create_admin_user(email, password, full_name)

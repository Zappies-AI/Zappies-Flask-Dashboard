import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# These are for your main authentication Supabase project
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

# Initialize the Supabase client using the service role key
# This bypasses RLS and allows us to insert the credentials
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Define the user and bot credentials
test_email = "roseovis@gmail.com"
test_password = "p@ssword1234"
test_company_id = 2
test_bot_url = "https://xirlamryohwhveunabha.supabase.co"
test_bot_anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhpcmxhbXJ5b2h3aHZldW5hYmhhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTQ5NzcsImV4cCI6MjA3MTE3MDk3N30.nZLcgCOrsZvglYR60T47TFir_bNfG_E4jHLZ5HStgpM"

try:
    # Step 1: Create the user using Supabase's admin function.
    # We use 'create_user' instead of 'sign_up' to avoid the email confirmation
    # flow. The 'email_confirm' option set to True will mark the email as verified.
    print(f"Signing up user: {test_email}...")
    auth_response = supabase.auth.admin.create_user({"email": test_email, "password": test_password, "email_confirm": True})
    user = auth_response.user
    
    if user:
        print(f"User created successfully with ID: {user.id}")
        
        # Step 2: Insert their credentials into the `client_credentials` table.
        # The service role key bypasses the RLS policy here.
        print("Inserting credentials into client_credentials table...")
        insert_response = supabase.from_('client_credentials').insert({
            'user_id': user.id,
            'company_id': test_company_id,
            'supabase_url': test_bot_url,
            'supabase_anon_key': test_bot_anon_key
        }).execute()

        print("Credentials inserted successfully.")
    
except Exception as e:
    print(f"An error occurred: {e}")
    if hasattr(e, 'message'):
        print(f"Error details: {e.message}")

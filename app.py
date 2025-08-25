import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')

# Get Supabase credentials
supabase_url: str = os.environ.get('SUPABASE_URL')
supabase_anon_key: str = os.environ.get('SUPABASE_ANON_KEY')
# --- NEW: Get the Service Role Key ---
supabase_service_role_key: str = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

# Initialize the Supabase client for authentication (using anon key)
supabase: Client = create_client(supabase_url, supabase_anon_key)

@app.route('/')
def index():
    """Redirects to the login page."""
    return redirect(url_for('login'))

DEFAULT_PASSWORD = "p@ssword123"

# In your login() route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        error = None
        
        try:
            auth_response = supabase.auth.sign_in_with_password({'email': email, 'password': password})

            if auth_response and auth_response.session:
                user_id = auth_response.session.user.id
                
                # Fetch the client's specific Supabase credentials
                credentials_response = supabase.from_('client_credentials').select('*').eq('user_id', user_id).single().execute()
                
                if credentials_response.data:
                    client_creds = credentials_response.data
                    
                    # --- FIX: Set the session variables here, for all successful logins ---
                    session['user_id'] = user_id
                    session['company_id'] = client_creds.get('company_id')
                    session['supabase_url'] = client_creds.get('supabase_url')
                    session['supabase_anon_key'] = client_creds.get('supabase_anon_key')
                    # --- END FIX ---
                    
                    # Check if the user is logging in with the default password
                    if password == DEFAULT_PASSWORD:
                        # Set a flag to force a password change
                        session['force_password_change'] = True
                        return redirect(url_for('change_password'))
                    else:
                        # If not using default password, proceed to dashboard
                        session['force_password_change'] = False
                        return redirect(url_for('dashboard'))
                else:
                    error = "No bot credentials found for this account. Please contact support."
            else:
                error = "Invalid email or password."
        
        except Exception as e:
            error = "Authentication failed. Please check your credentials."
            print(f"Authentication error: {e}")

        return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session or not session.get('force_password_change'):
        return redirect(url_for('dashboard'))

    error = None
    success = None
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            error = "Passwords do not match."
        elif len(new_password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            try:
                # --- FIX: Create a new client instance with the service role key ---
                # This client has the necessary permissions to update user passwords
                supabase_admin: Client = create_client(supabase_url, supabase_service_role_key)
                
                # Use the admin client to update the user's password
                supabase_admin.auth.admin.update_user_by_id(session['user_id'], {'password': new_password})
                
                # Also use the admin client to update the custom flag in the client_credentials table
                supabase_admin.from_('client_credentials').update({'is_default_password': False}).eq('user_id', session['user_id']).execute()
                
                # Password successfully updated, clear the flag
                session['force_password_change'] = False
                success = "Your password has been changed successfully."
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                error = "Failed to update password. Please try again."
                print(f"Password update error: {e}")
    
    return render_template('change_password.html', error=error, success=success)

@app.route('/dashboard')
def dashboard():
    """
    Displays the client dashboard.
    
    This route dynamically connects to the client's specific database using credentials
    stored in the session and fetches the relevant data.
    """
    # Check if the user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Retrieve client's unique credentials from the session
    supabase_url_client = session.get('supabase_url')
    supabase_anon_key_client = session.get('supabase_anon_key')
    company_id = session.get('company_id')

    # Guard against missing credentials
    if not supabase_url_client or not supabase_anon_key_client or not company_id:
        session.clear()
        return redirect(url_for('login'))

    # Initialize data variables with default values to avoid Jinja2 errors
    bot_stats = {
        'total_messages': 0, 'total_recipients': 0, 'total_conversions': 0, 
        'avg_response_time_ms': 0, 'updated_at': 'N/A'
    }
    chart_labels = []
    chart_data = []
    whatsapp_users = []
    error = None

    try:
        # Create a new Supabase client instance dynamically for the client's database
        client_bot_db: Client = create_client(supabase_url_client, supabase_anon_key_client)

        # Fetch all statistics from the client's database, filtered by company_id
        stats_response = client_bot_db.from_('bot_statistics').select('*').eq('company_id', company_id).execute()
        if stats_response.data:
            # Safely get the first element if the list is not empty
            bot_stats = stats_response.data[0]
        
        # Fetch conversation counts for the last 7 days for the chart
        seven_days_ago = datetime.now() - timedelta(days=7)
        conversations_response = client_bot_db.from_('conversations').select('updated_at').eq('company_id', company_id).gt('updated_at', seven_days_ago.isoformat()).execute()

        # Process data for the chart
        conversation_counts = {}
        for conv in conversations_response.data:
            date_str = conv['updated_at'].split('T')[0]
            if date_str in conversation_counts:
                conversation_counts[date_str] += 1
            else:
                conversation_counts[date_str] = 1

        chart_labels = sorted(conversation_counts.keys())
        chart_data = [conversation_counts[date] for date in chart_labels]

        # Fetch a list of all WhatsApp users using the correct column names
        users_response = client_bot_db.from_('whatsapp_users').select('*').eq('company_id', company_id).execute()
        whatsapp_users = users_response.data or []
        
    except Exception as e:
        print(f"Error fetching data for dashboard: {e}")
        error = "Could not retrieve dashboard data. Please try again later."
    
    return render_template(
        'dashboard.html', 
        bot_stats=bot_stats,
        chart_labels=chart_labels,
        chart_data=chart_data,
        whatsapp_users=whatsapp_users,
        error=error
    )

@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/conversation/<user_id>')
def get_conversation(user_id):
    """
    Fetches the conversation history for a specific user based on the database schema.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    supabase_url_client = session.get('supabase_url')
    supabase_anon_key_client = session.get('supabase_anon_key')

    if not supabase_url_client or not supabase_anon_key_client:
        return jsonify({'error': 'Missing credentials'}), 401

    try:
        client_bot_db: Client = create_client(supabase_url_client, supabase_anon_key_client)
        
        # Step 1: Find the internal user ID (whatsapp_users.id) using the wa_id
        wa_user_response = client_bot_db.from_('whatsapp_users').select('id').eq('wa_id', user_id).single().execute()
        
        if not wa_user_response.data:
            # If no user is found with that wa_id, return an empty list
            return jsonify([])
        
        wa_user_id = wa_user_response.data.get('id')

        # Step 2: Find the conversation ID (conversations.id) using the internal user ID
        conversation_response = client_bot_db.from_('conversations').select('id').eq('user_id', wa_user_id).single().execute()
        
        if not conversation_response.data:
            # If no conversation is found, return an empty list
            return jsonify([])

        conversation_id = conversation_response.data.get('id')
        
        # Step 3: Fetch the messages using the retrieved conversation_id
        messages_response = client_bot_db.from_('messages').select('content, sender_type, timestamp').eq('conversation_id', conversation_id).order('timestamp', desc=False).execute()
        
        # Reformat the messages for the front-end
        formatted_messages = []
        for msg in messages_response.data:
            formatted_messages.append({
                'from': 'bot' if msg['sender_type'] == 'bot' else 'user',
                'text': msg['content']
            })

        return jsonify(formatted_messages)

    except Exception as e:
        print(f"Error fetching conversation: {e}")
        return jsonify({'error': 'Error fetching conversation'}), 500

if __name__ == '__main__':
    # You should run this in production with a proper WSGI server (e.g., Gunicorn)
    # For development, you can use:
    app.run(debug=True)

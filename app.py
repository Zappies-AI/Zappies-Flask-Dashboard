# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
import os
import jwt
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)
# Enable CORS for the frontend.
CORS(app)

# Retrieve Supabase credentials from environment variables for security.
SUPABASE_AUTH_URL = os.getenv("SUPABASE_AUTH_URL")
SUPABASE_AUTH_ANON_KEY = os.getenv("SUPABASE_AUTH_ANON_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Initialize the Supabase client for the AUTHENTICATION database.
try:
    auth_supabase_client: Client = create_client(SUPABASE_AUTH_URL, SUPABASE_AUTH_ANON_KEY)
except Exception as e:
    print(f"Error initializing Supabase Auth Client: {e}")
    auth_supabase_client = None

# A template for the .env file to be used in production.
env_template = """
# .env file template for the Flask backend.
# This file should not be committed to version control.

# URL and anon key for your Supabase Authentication project.
SUPABASE_AUTH_URL="YOUR_SUPABASE_AUTH_URL"
SUPABASE_AUTH_ANON_KEY="YOUR_SUPABASE_AUTH_ANON_KEY"

# JWT secret key for decoding tokens. Find this in your Supabase project settings.
SUPABASE_JWT_SECRET="YOUR_SUPABASE_JWT_SECRET"
"""

@app.route('/api/login', methods=['POST'])
def login():
    """
    Authenticates a user using Supabase's built-in authentication.
    """
    if auth_supabase_client is None:
        return jsonify({'error': 'Backend not configured properly.'}), 500

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({'error': 'Email and password are required'}), 400

    try:
        # Use Supabase's sign_in_with_password method
        response = auth_supabase_client.auth.sign_in_with_password({'email': email, 'password': password})
        session = response.session

        if not session:
            return jsonify({'error': 'Invalid email or password'}), 401

        # Retrieve the user's custom data from your 'users' table
        # using the user's ID from the Supabase session.
        user_id = session.user.id
        user_data_response = auth_supabase_client.table('users').select('*').eq('id', user_id).limit(1).execute()
        user_data = user_data_response.data
        
        if not user_data:
            return jsonify({'error': 'User data not found'}), 404

        user = user_data[0]

        # Return the necessary details and the JWT access token to the frontend.
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'access_token': session.access_token,
            'company_id': user['company_id'],
            'supabase_url': user['supabase_url'],
            'supabase_anon_key': user['supabase_anon_key']
        }), 200

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'An internal server error occurred during login'}), 500

@app.route('/api/dashboard_data', methods=['POST'])
def get_dashboard_data():
    """
    Fetches bot statistics for a specific company from their
    dedicated Supabase project. Requires a valid JWT token.
    """
    # Check for the Authorization header with a Bearer token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization token is missing or invalid'}), 401
    
    token = auth_header.split(" ")[1]

    try:
        # Verify the token using your Supabase JWT secret
        decoded_token = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        user_id = decoded_token['sub']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    
    # We will get the credentials from the request body as before,
    # but in a production application, you would fetch these from a
    # secure database based on the user_id from the token.
    data = request.get_json()
    company_id = data.get('company_id')
    supabase_url = data.get('supabase_url')
    supabase_anon_key = data.get('supabase_anon_key')

    if not all([company_id, supabase_url, supabase_anon_key]):
        return jsonify({'error': 'Missing required data'}), 400

    try:
        # Initialize the Supabase client for the BOT'S data database.
        bot_supabase_client: Client = create_client(supabase_url, supabase_anon_key)
        
        # Query the 'bot_statistics' table.
        # We assume this table has a company_id column as per your security model.
        response = bot_supabase_client.table('bot_statistics').select('*').eq('company_id', company_id).limit(1).execute()
        
        if response.data:
            bot_stats = response.data[0]
            
            # Dummy data for the chart, as per the previous version.
            chart_data = [
                {"date": "2023-01-01", "total_messages": bot_stats["total_messages"] * 0.8},
                {"date": "2023-01-02", "total_messages": bot_stats["total_messages"] * 0.9},
                {"date": "2023-01-03", "total_messages": bot_stats["total_messages"]},
            ]

            return jsonify({
                'success': True,
                'stats': bot_stats,
                'chartData': chart_data
            }), 200
        else:
            return jsonify({'error': 'No statistics found for this company.'}), 404

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An internal server error occurred'}), 500

if __name__ == '__main__':
    # You might need to set your SUPABASE_AUTH_URL and SUPABASE_AUTH_ANON_KEY
    # as environment variables or directly in the code for local testing.
    app.run(debug=True, port=5000)

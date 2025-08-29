from supabase import create_client, Client

# Supabase credentials
SUPABASE_URL = "https://fzliiwigydluhgbuvnmr.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ6bGlpd2lneWRsdWhnYnV2bm1yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5MjkxNTMsImV4cCI6MjA1NzUwNTE1M30.w3Y7W14lmnD-gu2U4dRjqIhy7JZpV9RUmv8-1ybQ92w"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# User credentials
email = "maxrai788@gmail.com"
password = "Maxrai123@"

# Sign in
def login(email, password):
    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
    if response.user:
        print("Login successful:", response.user)
    else:
        print("Login failed:", response)

# Run login
login(email, password)

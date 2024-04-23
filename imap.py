import imaplib
import email
import datetime

# IMAP server configuration
IMAP_SERVER = 'imap.gmail.com'
IMAP_PORT = 993
EMAIL = 'maxrai788@gmail.com'
PASSWORD = 'rqcuswodywcazihj'

# Connect to the IMAP server
mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)

# Login to the server
mail.login(EMAIL, PASSWORD)

# Select the mailbox (e.g., INBOX)
mail.select('INBOX')

# Calculate the start of today
today = datetime.date.today()
start_of_today = today.strftime('%d-%b-%Y')

# Define the search criteria for unseen emails received today
search_criteria = f'(UNSEEN SINCE "{start_of_today}")'

# Search for email messages with the specified subject received within today
status, messages = mail.uid('search', None, search_criteria)

# Fetch and process the email messages
for num in messages[0].split():
    status, data = mail.uid('fetch', num, '(RFC822)')
    if status == 'OK':
        raw_email = data[0][1]
        email_message = email.message_from_bytes(raw_email)
        from_address = email_message['From']
        to_address = email_message['To']
        subject = email_message['Subject']
        date = email_message['Date']
        
        # Extract plain text message body
        message_body = ""
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                message_body = part.get_payload(decode=True).decode()
        
        print(f'From: {from_address}\nTo: {to_address}\nSubject: {subject}\nDate: {date}\nMessage Body:\n{message_body}\n')

# Close the connection
mail.close()

# Logout from the server
mail.logout()

def save_csv_record_in_db(self, csv_file_path):
    try:
        # Unpack the elements of csv_file_path
        name, created_at, updated_at, created_date = csv_file_path

        # Prepare the SQL query
        insert_query = """
            INSERT INTO pick_bin_snapshot_records (name, created_at, updated_at, created_date)
            VALUES (%s, %s, %s, %s)
        """

        # Execute the SQL query with individual parameters
        self.execute_sql(insert_query, params=(name, created_at, updated_at, created_date), commit=True)
        return True
           
    except mysql.connector.Error as e:
        print("Error saving CSV record to database:", e)
        return False
    except Exception as e:
        print("Error:", e)
        return False

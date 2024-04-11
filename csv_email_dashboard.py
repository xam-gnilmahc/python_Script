import mysql.connector
import csv
from datetime import datetime, timedelta
from pytz import timezone
import smtplib,ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import imaplib
import email


class TaskExporter:

    def __init__(self):
        self.host = "localhost"
        self.database = "tdm"
        self.user = "root"
        self.password = ""
        self.connection = None
        self.sender_email = ""
        self.sender_password = ""
        self.recipients = ["maxrai788@gmail.com", "max.c@shikhartech.com"]

    def connect_to_database(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return True
        except mysql.connector.Error as e:
            print("Error connecting to MySQL:", e)
            return False

    def get_tasks_by_user_id(self, user_id):
        try:
            if not self.connection:
                if not self.connect_to_database():
                    return None

            cursor = self.connection.cursor(dictionary=True)

            # cursor.execute(f"SELECT DISTINCT taskId FROM task_collaborators WHERE collaborator = {user_id}")
            # task_ids = [row['taskId'] for row in cursor.fetchall()]
            # ({','.join(map(str, task_ids))})

            cursor.execute(f""" 
                SELECT
                    tasks.id, tasks.title, tasks.created_at, tasks.priority, tasks.deadline,
                    CASE
                    WHEN tasks.status = "0" THEN "Assigned"
                    WHEN tasks.status = "1" THEN "Progress"
                    END AS Status,
                    (SELECT name FROM users WHERE users.id = tasks.createdBy) AS createdBy,
                    (SELECT name FROM projects WHERE projects.id = tasks.project_id) AS projectName,
                    COALESCE(tc1.flag, "") AS isAssignee,
                    COALESCE(tc2.flag, "") AS isReviewer,
                    GROUP_CONCAT((SELECT name FROM users WHERE users.id = task_collaborators.collaborator)) AS collaborator_names
                FROM
                    tasks
                LEFT JOIN 
                    task_collaborators AS tc1
                ON
                    tasks.id = tc1.taskId AND tc1.collaborator = {user_id} AND tc1.flag = '0'
                LEFT JOIN 
                    task_collaborators AS tc2
                ON
                    tasks.id = tc2.taskId AND tc2.collaborator = {user_id} AND tc2.flag = '1'
                LEFT JOIN
                    task_collaborators
                ON
                    tasks.id = task_collaborators.taskId
                WHERE
                    tasks.id IN (SELECT DISTINCT taskId FROM task_collaborators WHERE collaborator = {user_id})  AND tasks.status IN ('0', '1', '2', '3')
                GROUP BY
                    tasks.id
                ORDER BY
                    tasks.priority DESC, tasks.id DESC
            """)

            data = cursor.fetchall()

            cursor.close()

            return data

        except mysql.connector.Error as e:
            print("Error retrieving tasks data:", e)
            return None

    def export_to_csv(self, tasks, file_path):
        try:
            if tasks:
                fieldnames = tasks[0].keys()
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(tasks)
                return file_path
            else:
                print("No tasks found.")
                return None
        except Exception as e:
            print("Error exporting data to CSV:", e)
            return None

    def save_csv_record_in_db(self, csv_file_path):
        try:
            if not self.connection:
                if not self.connect_to_database():
                    return False

            cursor = self.connection.cursor()
            insert_query = """
                INSERT INTO pick_bin_snapshot_records ( name, created_at, updated_at, created_date)
                VALUES ( %s, %s, %s, %s)
            """

            cursor.executemany(insert_query, csv_file_path)
            self.connection.commit()
            cursor.close()
            return True
        except mysql.connector.Error as e:
            print("Error saving CSV record to database:", e)
            return False
        except Exception as e:
            print("Error:", e)
            return False

    def connect_to_smtp_server(self):
        try:
            context = ssl.create_default_context()

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls(context=context)
            server.login(self.sender_email, self.sender_password)
            return server
        except Exception as e:
            print("Error connecting to SMTP server:", e)
            return None

    def send_email(self, file_path):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ", ".join(self.recipients)
            msg['Subject'] = "Tasks Data"

            body = "Please find attached the tasks data CSV file. [https://realpython.com/python-send-email/]"
            msg.attach(MIMEText(body, 'plain'))

            attachment = open(file_path, "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', "attachment; filename= " + file_path.split('/')[-1])
            msg.attach(part)

            server = self.connect_to_smtp_server()
            if server:
                text = msg.as_string()
                server.sendmail(self.sender_email, self.recipients, text)
                server.quit()
                return True
            else:
                return False

        except Exception as e:
            print("Error sending email:", e)
            return False
        
        
    def connect_to_imap_server(self):
        try:
            server = imaplib.IMAP4_SSL("imap.gmail.com",993)
            server.login(self.sender_email, self.sender_password)
            server.select("inbox")
            return server
        except Exception as e:
            print("Error connecting to IMAP server:", e)
            return None

    def fetch_latest_email(self):
        try:
            server = self.connect_to_imap_server()
            if server:
                current_date = datetime.now().date()
                start_of_today = current_date.strftime('%d-%b-%Y')
                search_criteria = f'(UNSEEN SINCE "{start_of_today}")'
                status, messages = server.uid('search', None, search_criteria)
                for num in messages[0].split():
                    status,data = server.uid('fetch', num, '(RFC822)')
                    
                    if status == 'OK':
                        raw_email = data[0][1]
                        email_message=email.message_from_bytes(raw_email)
                        from_address = email_message['From']
                        to_address = email_message['To']
                        subject = email_message['Subject']
                        date = email_message['Date']
                        
                        message_body = ""
                        for part in email_message.walk():
                            
                            content_type = part.get_content_type()
                            if content_type == 'text/plain':
                                message_body = part.get_payload(decode=True).decode()
                        
                        print(f'From: {from_address}\nTo: {to_address}\nSubject: {subject}\nDate: {date}\nMessage Body:\n{message_body}\n')

        except Exception as e:
            print("Error fetching latest email:", e)
            return None
        
    # def process_latest_email(self):
    #     try:
    #         latest_email = self.fetch_latest_email()
    #         if latest_email:
    #             message_body = None
    #             for part in latest_email.walk():
    #                 content_type = part.get_content_type()
    #                 if content_type == 'text/plain':
    #                    message_body = part.get_payload()
    #                    break
            
    #             if message_body:
    #                print("Message body:", message_body)
    #             else:
    #                print("No plain text message body found.")
    #         else:
    #            print("No email found.")
            
           
    #     except Exception as e:
    #         print("Error processing latest email:", e)
    #         return None


    def export_tasks_and_send_email(self, user_id):
        try:
            # Get tasks data
            tasks_data = self.get_tasks_by_user_id(user_id)
            if not tasks_data:
                print("No tasks found for user with ID", user_id)
                return False

            # Export tasks to CSV
            csv_file_path = f'D:/task/tasks_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
            if not self.export_to_csv(tasks_data, csv_file_path):
                print("Failed to export tasks data to CSV.")
                return False

            # Save CSV record in database
            csv_log_data = [(csv_file_path, datetime.now(), datetime.now(), datetime.now().date())]
            if not self.save_csv_record_in_db(csv_log_data):
                print("Failed to save CSV record in database.")
                return False

            # Send email with CSV attachment
            if not self.send_email(csv_file_path):
                print("Failed to send email.")
                return False
            
            mingo =  self.fetch_latest_email()
                # print("Failed to get latest email")
                # return False
            print(f"{mingo}")
            print("Tasks data exported to CSV file and email sent successfully.")
            return True
        except Exception as e:
            print("Error:", e)
            return False
     


# Example usage
task_exporter = TaskExporter()
user_id = 1
if not task_exporter.export_tasks_and_send_email(user_id):
    print("Failed to export tasks data and send email.")

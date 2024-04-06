import mysql.connector
import csv

class TaskExporter:
    def __init__(self):
        self.host = "localhost"
        self.database = "tdm"
        self.user = "root"
        self.password = ""
        self.connection = None
        
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
            cursor.execute(f'''SELECT tasks.*, 
                (SELECT name FROM users WHERE users.id = tasks.createdBy) AS createdBy,
                (SELECT name FROM users WHERE users.id = tasks.assignedBy LIMIT 1) AS assignedBy,
                (SELECT name FROM users WHERE users.id = tasks.completedBy LIMIT 1) AS completedBy,
                (SELECT GROUP_CONCAT(type) FROM tasktypes JOIN task_tasktypes_pivot ON tasktypes.id = task_tasktypes_pivot.tasktypes_id WHERE task_tasktypes_pivot.task_id = tasks.id) as types,
                task_collaborators.id AS collaborator_id,
                task_collaborators.collaborator,
                task_collaborators.taskId AS collaborator_taskId,
                task_collaborators.flag AS collaborator_flag,
                (SELECT name FROM users WHERE task_collaborators.collaborator = users.id) AS collaborator_name
                FROM tasks
                LEFT JOIN task_collaborators ON tasks.id = task_collaborators.taskId
                WHERE task_collaborators.flag = "0"
                GROUP BY taskId
                ''')

            tasks = cursor.fetchall()
            cursor.close()

            return tasks

        except mysql.connector.Error as e:
            print("Error retrieving tasks data:", e)
            return None

    def export_to_csv(self, tasks, file_path):
        if tasks:
            fieldnames = tasks[0].keys()
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(tasks)
            print("CSV file created successfully at:", file_path)
        else:
            print("No tasks found.")

# Example usage:
task_exporter = TaskExporter()
user_id = 1
tasks_data = task_exporter.get_tasks_by_user_id(user_id)
if tasks_data:
    csv_file_path = 'D:/tasks.csv'
    task_exporter.export_to_csv(tasks_data, csv_file_path)
else:
    print("No tasks found.")

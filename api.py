import requests
import mysql.connector
import json
from datetime import datetime, timedelta
class Imdb_API:
    def __init__(self, api_url):
        self.api_url = api_url
        self.host = "localhost"
        self.database = "tdm"
        self.user = "root"
        self.password = "123"
        self.connection = None
        self.imd_key="eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyMDQzNGU5ODU2ZWZmZmYyOWViM2M4ZWQ5YmIxNjUwZiIsInN1YiI6IjY0ODg3ZDRhZTI3MjYwMDE0N2JiOGUyNyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.VItISvI0UXm3VAb_K2TgC5fNBOKCW1uO4L3VNRB3chc"
        
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

    def get_products(self):
        # Make a GET request to the API 
        api_key = self.imd_key
        
        headers = {
           "accept": "application/json",
           "Authorization": "Bearer " + api_key
        }

        response = requests.get(self.api_url, headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            products = response.json()
           # return products['results']
        
           # Create an empty list to store the data
            data = []

            # Extract relevant data from each product
            for product in products.get('results',[]):
                #genre_ids = ','.join(map(str, product['genre_ids']))
                data.append((
                     product['original_name'],
                     datetime.now(),
                     datetime.now(),
                     datetime.now()
                     #genre_ids
                ))
              
            try:
                if not self.connection:
                    if not self.connect_to_database():
                        return None

                cursor = self.connection.cursor()

                # Split the data into chunks of size 10
                chunkSize = 10
                data_chunks = [data[i:i + chunkSize] for i in range(0, len(data), chunkSize)]

                # Execute insert query for each chunk of data
                for chunk in data_chunks:
                    # Execute SQL query to insert data into the database
                    insert_query = """
                    INSERT INTO pick_bin_snapshot_records (name,  created_at, updated_at, created_date)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.executemany(insert_query, chunk)
                    self.connection.commit()

                cursor.close()
                print("product insert into database successfully")
                return True

            except mysql.connector.Error as e:
                print("Error inserting products data into the database:", e)
                return False
            
        else:
            # If the request was unsuccessful, return None
            #print("Error:", response.status_code)
            return False
        
# Example usage:
if __name__ == "__main__":
    api = Imdb_API("https://api.themoviedb.org/3/discover/tv?include_adult=false&include_null_first_air_dates=false&language=en-US&page=1&sort_by=popularity.desc")
    products_data = api.get_products()
    print(products_data)
        # print("failed to saved into database");
        


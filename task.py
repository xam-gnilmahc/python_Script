import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta

def scrape_uci_datasets():
    base_url = "https://archive.ics.uci.edu/datasets"

    # CSV headers
    headers = [
        "Dataset Name", "Donated Date", "Description",
        "Dataset Characteristics", "Subject Area", "Associated Tasks",
        "Feature Type", "Instances", "Features"
    ]

    data = []

    def scrape_dataset_details(dataset_url):
        response = requests.get(dataset_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        dataset_name = soup.find('h1', class_='text-3xl font-semibold text-primary-content')
        dataset_name = dataset_name.text.strip() if dataset_name else "N/A"

        donated_date = soup.find('h2', class_='text-sm text-primary-content')
        donated_date = donated_date.text.strip().replace('Donated on ', '') if donated_date else "N/A"

        description = soup.find('p', class_='svelte-1xc1tf7')
        description = description.text.strip() if description else "N/A"

        details = soup.find_all('div', class_='col-span-4')

        dataset_characteristics = details[0].find('p').text.strip() if len(details) > 0 else "N/A"
        subject_area = details[1].find('p').text.strip() if len(details) > 1 else "N/A"
        associated_tasks = details[2].find('p').text.strip() if len(details) > 2 else "N/A"
        feature_type = details[3].find('p').text.strip() if len(details) > 3 else "N/A"
        instances = details[4].find('p').text.strip() if len(details) > 4 else "N/A"
        features = details[5].find('p').text.strip() if len(details) > 5 else "N/A"

        return [
            dataset_name, donated_date, description, dataset_characteristics,
            subject_area, associated_tasks, feature_type, instances, features
        ]
        
    def scrape_datasets(page_url):
        response = requests.get(page_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        dataset_list = soup.find_all('a', class_='link-hover link text-xl font-semibold')

        if not dataset_list:
            print("No dataset links found")
            return

        for dataset in dataset_list:
            dataset_link = "https://archive.ics.uci.edu" + dataset['href']
            print(f"Scraping details for {dataset.text.strip()}...")
            dataset_details = scrape_dataset_details(dataset_link)
            data.append(dataset_details)

    page_urls = [
        "https://archive.ics.uci.edu/datasets?skip=0&take=10& sort=desc&orderBy=NumHits&search=",
        "https://archive.ics.uci.edu/datasets?skip=10&take=20&sort=desc&orderBy=NumHits&search=",
        "https://archive.ics.uci.edu/datasets?skip=20&take=30&sort=desc&orderBy=NumHits&search="
    ]

    for page_url in page_urls:
        print(f"Scraping page: {page_url}")
        scrape_datasets(page_url)
    
    csv_file_path = f'D:/task/scrapping_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
    with open( csv_file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(data)

    print("Data scraping and saving to CSV complete!")


scrape_uci_datasets()

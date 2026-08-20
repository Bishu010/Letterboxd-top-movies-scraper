# Letterboxd Top Movies Scraper

A Python web scraper that collects highly-rated movies from Letterboxd for a selected year and saves the results as a CSV dataset.

The project uses Selenium to access Letterboxd pages, BeautifulSoup to parse HTML, and JSON-LD structured data to extract movie information.

## Features

- Select a movie year from the command line
- Choose how many top-rated movies to collect
- Extract movie title
- Extract director(s)
- Extract Letterboxd rating
- Extract genres
- Extract runtime
- Extract available streaming/platform information when listed
- Save results automatically as a CSV file
- Uses Selenium to handle browser-rendered pages

## Technologies Used

- Python
- Selenium
- BeautifulSoup
- JSON / JSON-LD
- CSV
- tqdm

## Project Structure

```text
Letterboxd-top-movies-scraper/
│
├── letterboxd_movie_scraper.py
├── requirements.txt
├── README.md
├── .gitignore
│
└── DataSets/

## Running the Scraper

This project uses Selenium to automate Google Chrome.

For the easiest setup, run the scraper on a local computer with Google Chrome installed.

```bash
pip install -r requirements.txt
python letterboxd_movie_scraper.py

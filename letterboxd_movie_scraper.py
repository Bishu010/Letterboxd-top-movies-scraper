import csv
import datetime
import json
import os
import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from tqdm import tqdm


def get_film_details(driver, film_url: str) -> dict:
    details = {
        'Title': 'N/A',
        'Director': 'N/A',
        'Rating': 'N/A',
        'Genres': 'N/A',
        'Runtime': 'N/A',
        'Platforms': 'N/A'
    }

    try:
        # Open the movie page using Selenium
        driver.get(film_url)
        time.sleep(1.5)

        # Get the HTML of the current page
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # ---------------------------------------------------------
        # Parse JSON-LD structured metadata
        # ---------------------------------------------------------

        script_tag = soup.find(
            'script',
            type='application/ld+json'
        )

        if script_tag and script_tag.string:

            clean_json = (
                script_tag.string
                .replace('/* <![CDATA[ */', '')
                .replace('/* ]]> */', '')
                .strip()
            )

            try:
                data = json.loads(clean_json)

                # -------------------------------------------------
                # Title
                # -------------------------------------------------

                if data.get('name'):
                    details['Title'] = data['name']

                # -------------------------------------------------
                # Director
                # -------------------------------------------------

                directors = data.get('director', [])

                if isinstance(directors, list):

                    director_names = [
                        d.get('name')
                        for d in directors
                        if isinstance(d, dict) and d.get('name')
                    ]

                    if director_names:
                        details['Director'] = ", ".join(
                            director_names
                        )

                elif isinstance(directors, dict):

                    details['Director'] = directors.get(
                        'name',
                        'N/A'
                    )

                # -------------------------------------------------
                # Rating
                # -------------------------------------------------

                rating_data = data.get(
                    'aggregateRating',
                    {}
                )

                if isinstance(rating_data, dict):

                    rating = rating_data.get(
                        'ratingValue'
                    )

                    if rating:

                        try:
                            details['Rating'] = (
                                f"{float(rating):.2f} / 5"
                            )
                        except (ValueError, TypeError):
                            details['Rating'] = str(rating)

                # -------------------------------------------------
                # Genres
                # -------------------------------------------------

                genres = data.get('genre', [])

                if isinstance(genres, list):

                    if genres:
                        details['Genres'] = ", ".join(
                            str(genre)
                            for genre in genres
                        )

                elif isinstance(genres, str):

                    details['Genres'] = genres

                # -------------------------------------------------
                # Runtime
                # -------------------------------------------------

                duration = data.get('duration')

                if duration:

                    # Example:
                    # PT2H2M
                    # PT90M
                    match = re.search(
                        r'PT(?:(\d+)H)?(?:(\d+)M)?',
                        duration
                    )

                    if match:

                        hours = match.group(1)
                        minutes = match.group(2)

                        if hours and minutes:

                            details['Runtime'] = (
                                f"{hours}h {minutes}m"
                            )

                        elif hours:

                            details['Runtime'] = (
                                f"{hours}h"
                            )

                        elif minutes:

                            details['Runtime'] = (
                                f"{minutes} mins"
                            )

            except json.JSONDecodeError:

                print(
                    f"Could not parse JSON-LD for: {film_url}"
                )

        # ---------------------------------------------------------
        # Fallback title
        # ---------------------------------------------------------

        if details['Title'] == 'N/A':

            if soup.title:

                page_title = soup.title.get_text(
                    strip=True
                )

                # Letterboxd titles normally look like:
                #
                # Movie Name (2020) directed by ...
                #
                details['Title'] = page_title.split(
                    ' directed by '
                )[0]

        # ---------------------------------------------------------
        # Platforms
        # ---------------------------------------------------------

        watch_section = (
            soup.find(
                'section',
                class_='watch-panel'
            )
            or soup.find(
                'div',
                id='watch'
            )
        )

        if watch_section:

            services = set()

            # Look for service names in image alt attributes
            for img in watch_section.find_all('img'):

                alt = img.get('alt')

                if alt:
                    services.add(
                        alt.strip()
                    )

            # Look for service names in link titles
            for link in watch_section.find_all('a'):

                title = link.get('title')

                if title:
                    services.add(
                        title.strip()
                    )

            if services:

                details['Platforms'] = ", ".join(
                    sorted(services)
                )

            else:

                details['Platforms'] = (
                    "Check Letterboxd Link"
                )

        else:

            details['Platforms'] = "Not Listed"

    except Exception as error:

        print(
            f"\nCould not scrape {film_url}: {error}"
        )

    return details


def scrape_letterboxd_year(year: int, top_n: int) -> list[dict]:

    movies = []
    page = 1

    # Start Chrome
    driver = webdriver.Chrome()

    try:

        while len(movies) < top_n:

            url = (
                f"https://letterboxd.com/films/year/"
                f"{year}/by/rating/page/{page}/"
            )

            print(
                f"\nOpening page {page}..."
            )

            # Open the Letterboxd ranking page
            driver.get(url)

            # Give the page time to load
            time.sleep(3)

            # -----------------------------------------------------
            # Find movie links
            # -----------------------------------------------------

            movie_elements = driver.find_elements(
                By.CSS_SELECTOR,
                "a[href*='/film/']"
            )

            # IMPORTANT:
            # Convert Selenium elements into normal strings
            # BEFORE visiting another page.
            #
            # Otherwise Selenium gives us:
            # StaleElementReferenceException
            # -----------------------------------------------------

            movie_urls = []

            for element in movie_elements:

                try:

                    film_url = element.get_attribute(
                        "href"
                    )

                    if film_url:
                        movie_urls.append(
                            film_url
                        )

                except Exception:

                    continue

            # Remove duplicate URLs
            movie_urls = list(
                dict.fromkeys(movie_urls)
            )

            if not movie_urls:

                print(
                    "No movie links found."
                )

                break

            print(
                f"Found {len(movie_urls)} movie links."
            )

            # -----------------------------------------------------
            # Scrape each movie
            # -----------------------------------------------------

            for film_url in tqdm(
                movie_urls,
                desc=f"Scraping Page {page}",
                leave=False
            ):

                if len(movies) >= top_n:
                    break

                # Get movie information
                extra_details = get_film_details(
                    driver,
                    film_url
                )

                # Create movie dictionary
                movie = {
                    'Rank': len(movies) + 1,

                    'Title': extra_details.get(
                        'Title',
                        'N/A'
                    ),

                    'Year': year,

                    'Director': extra_details.get(
                        'Director',
                        'N/A'
                    ),

                    'Rating': extra_details.get(
                        'Rating',
                        'N/A'
                    ),

                    'Genres': extra_details.get(
                        'Genres',
                        'N/A'
                    ),

                    'Runtime': extra_details.get(
                        'Runtime',
                        'N/A'
                    ),

                    'Platforms': extra_details.get(
                        'Platforms',
                        'N/A'
                    ),

                    'URL': film_url
                }

                movies.append(movie)

                # Small delay between requests
                time.sleep(0.5)

            page += 1

    finally:

        # Always close Chrome
        driver.quit()

    return movies


def main():

    # Current year
    current_year = datetime.datetime.now().year

    # -------------------------------------------------------------
    # Get user input
    # -------------------------------------------------------------

    try:

        input_year = int(
            input(
                f"Enter the year to scrape "
                f"(1880–{current_year}): "
            )
        )

        top_n = int(
            input(
                "How many top movies do you want "
                "to fetch? (e.g., 10, 25, 50): "
            )
        )

    except ValueError:

        print(
            "Invalid numerical input."
        )

        return

    # -------------------------------------------------------------
    # Validate year
    # -------------------------------------------------------------

    if (
        input_year > current_year
        or input_year < 1880
    ):

        print(
            "Year out of valid range."
        )

        return

    # Validate number of movies
    if top_n <= 0:

        print(
            "Number of movies must be greater than 0."
        )

        return

    # -------------------------------------------------------------
    # Start scraping
    # -------------------------------------------------------------

    print(
        f"\nFetching Top {top_n} movies "
        f"from {input_year}...\n"
    )

    movie_list = scrape_letterboxd_year(
        input_year,
        top_n
    )

    # -------------------------------------------------------------
    # Check results
    # -------------------------------------------------------------

    if not movie_list:

        print(
            "No movie data collected."
        )

        return

    # -------------------------------------------------------------
    # Create DataSets directory
    # -------------------------------------------------------------

    dataset_dir = os.path.join(
        os.path.dirname(__file__),
        "DataSets"
    )

    os.makedirs(
        dataset_dir,
        exist_ok=True
    )

    # -------------------------------------------------------------
    # CSV file path
    # -------------------------------------------------------------

    file_path = os.path.join(
        dataset_dir,
        f"Letterboxd_Top{top_n}_{input_year}.csv"
    )

    # -------------------------------------------------------------
    # CSV columns
    # -------------------------------------------------------------

    fieldnames = [
        'Rank',
        'Title',
        'Year',
        'Director',
        'Rating',
        'Genres',
        'Runtime',
        'Platforms',
        'URL'
    ]

    # -------------------------------------------------------------
    # Write CSV
    # -------------------------------------------------------------

    with open(
        file_path,
        mode='w',
        newline='',
        encoding='utf-8'
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            movie_list
        )

    # -------------------------------------------------------------
    # Finished
    # -------------------------------------------------------------

    print(
        f"\nDone! Data saved successfully to:"
        f"\n{file_path}"
    )


if __name__ == "__main__":
    main()
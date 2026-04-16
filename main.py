import os
import logging
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
FLIGHT_HISTORY_URL = "https://www.flightradar24.com/data/aircraft/"
LOGIN_URL = "https://www.flightradar24.com"
TIMEOUT = 10000       # Playwright pakai milidetik
SLEEP_INTERVAL = 5000


# ──────────────────────────────────────────────
# Init browser
# ──────────────────────────────────────────────
def init_browser(playwright, headless=True):
    browser = playwright.chromium.launch(headless=headless)

    context = browser.new_context(
        viewport={"width": 1920, "height": 1080}
    )

    page = context.new_page()

    return browser, page


# ──────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────
def login_to_flightradar(page, username, password):
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        logging.info(f"Navigated to {LOGIN_URL}")

        # Terima cookie utama
        try:
            page.get_by_role("button", name="Close").click(timeout=TIMEOUT)
            logging.info("Clicked accept cookie")
        except:
            logging.info("No cookie accept button found")

        # Tutup cookie popup lain
        try:
            page.click(
                'xpath=/html/body/div[6]/div/div/div/div/div[2]/div[2]/button',
                timeout=TIMEOUT
            )
        except PlaywrightTimeout:
            logging.info("No secondary cookie button found")

        page.wait_for_timeout(3000)

        # Klik tombol login
        login_btn_xpath = (
            "xpath=/html/body/div[1]/div/div/div[2]/div/div/div/div[2]/div[2]/div[2]/button"
        )
        page.wait_for_selector(login_btn_xpath, timeout=TIMEOUT)
        page.click(login_btn_xpath)
        logging.info("Clicked login button")

        # Isi form
        email_input = page.locator(
            'input[data-testid="email"]').filter(visible=True)
        password_input = page.locator(
            'input[data-testid="password"]').filter(visible=True)
        email_input.wait_for(state="visible", timeout=TIMEOUT)

        email_input.fill(username)
        password_input.fill(password)

        # Submit
        submit_xpath = (
            "xpath=/html/body/div[5]/div/div/div/form/button")
        page.wait_for_selector(submit_xpath, timeout=TIMEOUT)
        page.click(submit_xpath)

        page.wait_for_timeout(5000)
        logging.info("Submitted login form")

        # Konfirmasi login berhasil
        success_xpath = (
            "xpath=/html/body/div[1]/div/div/div[2]/div/div/div/div[2]/div[2]/div[2]/button"
        )
        page.wait_for_selector(success_xpath, timeout=TIMEOUT)
        logging.info("Login success")

    except Exception as e:
        logging.error(f"Error during login: {e}")
        raise


# ──────────────────────────────────────────────
# Load earlier flights
# ──────────────────────────────────────────────
def load_earlier_flights(page, start_date):
    date_param = start_date - timedelta(days=2)

    while True:
        try:
            page.wait_for_selector("table", timeout=TIMEOUT)
            soup = BeautifulSoup(page.content(), "html.parser")
            table = soup.find("table")

            if not table:
                logging.warning("No flight table found")
                break

            rows = table.select("tbody tr")
            dates = []
            for row in rows:
                try:
                    date_text = row.select("td")[2].text.strip()
                    flight_date = datetime.strptime(date_text, "%d %b %Y")
                    dates.append(flight_date)
                except (IndexError, ValueError):
                    continue

            if not dates:
                logging.warning("No dates parsed from table rows")
                break

            if min(dates) < date_param:
                logging.info(f"Reached flights before {start_date}")
                break

            # Klik tombol load earlier
            try:
                page.wait_for_selector(
                    "#btn-load-earlier-flights",
                    state="visible",
                    timeout=TIMEOUT
                )
                page.click("#btn-load-earlier-flights")
                logging.info("Clicked 'Load earlier flights'")
                page.wait_for_timeout(5000)
            except PlaywrightTimeout:
                logging.info("No more earlier flights to load")
                break

        except Exception as e:
            logging.error(f"Error loading earlier flights: {e}")
            break


# ──────────────────────────────────────────────
# Parse flight history
# ──────────────────────────────────────────────
def parse_flight_history(page, airline, aircraft_registration, start_date=None, end_date=None):
    soup = BeautifulSoup(page.content(), "html.parser")
    table = soup.find("table")

    if not table:
        logging.warning("No flight history table found")
        return pd.DataFrame()

    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    rows = []

    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]

        if len(cells) != len(headers):
            continue

        flight = dict(zip(headers, cells))

        date_str = flight.get("DATE") or flight.get("Date") or cells[2]
        try:
            flight_date = datetime.strptime(date_str, "%d %b %Y")
        except ValueError:
            continue

        if start_date and flight_date < start_date:
            continue
        if end_date and flight_date > end_date:
            continue

        flight["airline_id"] = airline
        flight["aircraft_registration"] = aircraft_registration
        rows.append(flight)

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
# Save to parquet
# ──────────────────────────────────────────────
def save_flight_history_to_file(flight_history, carrier, registration):
    if flight_history.empty:
        logging.warning(f"No data to save for {registration}")
        return

    os.makedirs("data", exist_ok=True)
    filename = f"data/{carrier}_{registration}_flightHistory.parquet"

    # Tambahkan .copy() agar tidak terjadi SettingWithCopyWarning
    df = flight_history.copy()
    df = df.loc[:, df.columns != ""]
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df["date"] = pd.to_datetime(df["date"])
    df.to_parquet(filename, index=False)
    logging.info(f"Saved flight history to {filename}")


# ──────────────────────────────────────────────
# Scrape per aircraft
# ──────────────────────────────────────────────
def scrape_flight_history(page, carrier, registration, start_date=None, end_date=None):
    logging.info(f"Scraping flight history for: {registration}")
    try:
        page.goto(
            f"{FLIGHT_HISTORY_URL}{registration}",
            wait_until="domcontentloaded"
        )
        load_earlier_flights(page, start_date)

        flights_df = parse_flight_history(
            page, carrier, registration, start_date, end_date
        )
        save_flight_history_to_file(flights_df, carrier, registration)

    except Exception as e:
        logging.error(f"Error scraping {registration}: {e}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":

    load_dotenv()
    username = os.getenv("USERNAMEE")
    password = os.getenv("PASSWORD")
    start_date = datetime.strptime(os.getenv("START_DATE"), "%Y-%m-%d")
    end_date = datetime.strptime(os.getenv("END_DATE"), "%Y-%m-%d")

    airline_data = pd.read_csv("airline/airline_registration.csv")

    with sync_playwright() as playwright:
        browser, page = init_browser(playwright)
        logging.info("Starting flight history scraping...")

        try:
            login_to_flightradar(page, username, password)

            airline = airline_data.columns[0]
            for aircraft in airline_data[airline].unique():
                scrape_flight_history(
                    page=page,        # nama arg tetap sama agar konsisten
                    carrier=airline,
                    registration=aircraft,
                    start_date=start_date,
                    end_date=end_date
                )
                time.sleep(5)
        finally:
            browser.close()
            logging.info("Browser closed")

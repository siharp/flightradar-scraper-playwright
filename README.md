# ✈️ FR24 Scraper (Playwright)

A simple scraper to collect flight history data from FlightRadar24 using Playwright.

---

## 📦 Requirements

* Docker
* Docker Compose (optional)
* `.env` file (for credentials & configuration)

---

## ⚙️ Build Docker Image

Run the following command from the project root:

```bash
docker build -t fr24-scraper-playwright:1.0.0 .
```

---

## 🚀 Run the Container

### 1. Prepare output folder

```bash
mkdir data
```

---

### 2. Run container with mounted output folder

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  fr24-scraper-playwright:1.0.0
```

---

## 📁 Mounting Explanation

```bash
-v $(pwd)/data:/app/data
```

This means:

* `$(pwd)/data` → folder on your host machine
* `/app/data` → folder inside the container

👉 All scraping results will be saved to the `data/` folder on your host.

---

## 📊 Mounting Airline Data (Optional)

If you want to provide your own airline dataset (CSV), you can mount it into the container.

### Example:

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/airline:/app/airline \
  fr24-scraper-playwright:1.0.0
```

---

### 📁 Explanation

```bash
-v $(pwd)/airline:/app/airline
```

* `$(pwd)/airline` → folder on your host containing airline CSV
* `/app/airline` → folder inside container

👉 Your script will read:

```bash
/app/airline/airline_registration.csv
```

---

### 📌 Example Structure

```text
fr24-scraper/
├── data/
├── airline/
│   └── airline_registration.csv
├── Dockerfile
├── requirements.txt
├── .env
└── README.md
```

---

## 🔐 Environment Configuration (.env)

Example `.env` file:

```env
USERNAMEE=your_email
PASSWORD=your_password
START_DATE=2024-01-01
END_DATE=2024-12-31
```

---

## 📝 Output

Scraped data will be stored in `.parquet` format inside:

```bash
data/
```

---

## 🚀 Future Improvements

* Parallel scraping (async)
* Scheduling (cron / Airflow)
* Deployment to server / cloud

---

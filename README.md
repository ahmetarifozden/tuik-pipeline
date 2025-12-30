# TUIK Data Pipeline

This project is a comprehensive **ETL (Extract, Transform, Load)** pipeline designed to scrape, index, process, and serve statistical data from the [Turkish Statistical Institute (TUIK)](https://data.tuik.gov.tr).

It allows you to build a local database of TUIK statistics, search within them, download specific datasets (Excel), convert them to a machine-readable format (CSV/Database), and serve them via a REST API.

## Features

*   ** automated Indexing:** Scrapes TUIK categories and indexes thousands of dataset metadata into a local PostgreSQL database.
*   **Keyword Search & Download:** Search for datasets by keyword (e.g., "enflasyon", "yoksulluk") and download them efficiently.
*   **Normalization:** Automatically converts complex/human-readable Excel files into normalized, structured CSV data ("Tidy Data").
*   **API Support:** Serves the metadata and processed data via a FastAPI backend.
*   **Docker Ready:** Fully containerized for easy deployment.

## Prerequisites

*   **Docker & Docker Compose** (for the database)
*   **Python 3.11+**
*   **Poetry** (Python dependency manager)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd tuik-pipeline
    ```

2.  **Configuration:**
    Copy the example environment file and configure it (if necessary):
    ```bash
    cp .env.example .env
    ```
    *By default, it connects to a local PostgreSQL instance via Docker.*

3.  **Start the Database:**
    ```bash
    docker compose up -d db
    ```

4.  **Install Dependencies:**
    ```bash
    poetry install
    ```

---

## Usage Guide

The project is controlled via three main shell scripts:

### 1. `./bot.sh` (The Indexer)
**Purpose:** Initializes the system and updates the metadata index.

*   Checks if the Database container is running.
*   **Step 1:** Scrapes the main TUIK website to find all data categories (saves to `config/categories.yaml`).
*   **Step 2:** Crawls each category page to find available datasets (tables) and saves their metadata (Title, URL, Publish Date) to the `datasets` table in the database.
*   *Note: This does not download the actual Excel files, only the metadata for searching.*

```bash
./bot.sh
```

### 2. `./run_config.sh` (The ETL Worker)
**Purpose:** Searches, downloads, normalizes, and loads data based on a keyword.

*   Arguments:
    *   `keyword`: The term to search for (e.g., "tarım", "yoksulluk"). Use quotes for multiple words (e.g., "iş gücü").
*   **Workflow:**
    1.  **SEARCH:** Queries the local DB for datasets matching the keyword.
    2.  **DOWNLOAD:** Prompts the user to confirm. If yes, downloads the Excel files to `downloads/<keyword>/`.
    3.  **NORMALIZE:** Converts the downloaded Excel files into structured CSV files in `normalized/<keyword>/`. It handles flattening headers and cleaning data.
    4.  **LOAD:** Loads the clean CSV data into the `observations` table in the database.

```bash
./run_config.sh "yoksulluk"
```

### 3. `./run.sh` (The Server)
**Purpose:** Starts the API server.

*   Launches a FastAPI instance.
*   Provides endpoints to query datasets and view data.
*   Runs on `http://localhost:8000`.
*   API Documentation available at: `http://localhost:8000/docs`.

```bash
./run.sh
```

---

## Docker Usage (Alternative)

If you prefer not to install Python/Poetry locally, you can run the entire stack (App + DB) using Docker.

```bash
docker compose up --build
```
This will start the API server and Database. You can then access the API at `http://localhost:8000`.

## Project Structure

*   `src/tuik_pipeline/`: Main application source code.
    *   `core/`: Configuration, Database, Logging.
    *   `etl/`: Extract, Transform, Load logic (Downloaders, Normalizers).
    *   `models/`: SQLAlchemy database models.
    *   `api/`: FastAPI routes.
*   `scripts/`: Python entry points called by the shell scripts.
*   `config/`: YAML configuration files.
*   `downloads/`: Directory where raw Excel files are saved.
*   `normalized/`: Directory for processed CSV files.

Geliştirici: Arif Özden

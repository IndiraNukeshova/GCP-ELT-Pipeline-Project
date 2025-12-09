# GCP ELT Data Pipeline: Unstructured Log Analysis (Dataflow, GCS, BigQuery)

## 🌟 Project Overview

This project implements a robust Extract, Load, and Transform (ELT) pipeline on the Google Cloud Platform (GCP) to process unstructured user logs, perform sentiment analysis and topic extraction using Apache Beam, and load the clean, structured data into a data warehouse (BigQuery) for analytics.

This pipeline successfully transforms raw log messages into actionable metrics, providing insights into user feedback quality, delivery speed, and payment issues.

## ⚙️ Architecture

The pipeline leverages core GCP services for scalability, serverless processing, and **fault tolerance**.

| Component | Role |
| :--- | :--- |
| **Google Cloud Storage (GCS)** | Stores raw input data, serves as staging/temp location, and hosts the **Dead-Letter Queue (DLQ)** for malformed records. |
| **Apache Beam / Google Dataflow** | The serverless processing engine. Handles orchestration, scaling, **data branching (Success/DLQ)**, and the core ELT logic. |
| **Custom Beam Transforms** | Includes logic for parsing, **language detection**, **word counting**, sentiment analysis, and **error catching (DLQ routing)**. |
| **Google BigQuery** | The final data warehouse where clean, structured, and enriched logs are loaded for querying and visualization. |
---

## 🛠️ Prerequisites

To run this project, you must have the following installed and configured:

1.  **Python 3.8+**
2.  **Google Cloud CLI (gcloud CLI)**: Installed and authenticated.
    ```bash
    gcloud auth application-default login
    gcloud config set project bigdata-elt-project
    ```
3.  **Virtual Environment (venv)**: Activated and required packages installed.
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 How to Run the Pipeline

The pipeline is submitted to the Dataflow service using the command line, referencing the external dependency file (`setup.py`).

### 1. Setup Data and Dependencies

* **GCS Bucket:** Ensure your bucket, `gs://my-raw-data-pipeline-1985`, is created, and the folders `/staging/` and `/temp/` exist.
* **Input File:** Upload the raw data file to GCS:
    ```bash
    gsutil cp raw_logs.txt gs://my-raw-data-pipeline-1985/raw_logs.txt
    ```

### 2. Execute Dataflow Job

Execute the pipeline from your project directory:

```
python3 pipeline.py \
    --setup_file=./setup.py \
    --runner=DataflowRunner \
    --project=bigdata-elt-project \
    --region=us-central1 \
    --temp_location=gs://my-raw-data-pipeline-1985/temp/ \
    --staging_location=gs://my-raw-data-pipeline-1985/staging/
```

### 3. Verify Job Status

Monitor the job status in the GCP Console: https://console.cloud.google.com/dataflow/jobs/us-central1/2025-12-04_03_58_59-4738100552860488039?project=bigdata-elt-project

## 📊 Results and Analysis

The pipeline was successfully run with new logic to detect the language and calculate word count. 
Crucially, the **Sentiment Analysis (TextBlob)** logic was set to execute only for messages where `language_code` is 'en', resulting in `NULL` values for non-English data, thus preventing analytical errors.

### BigQuery Verification Query

The following SQL query was executed to confirm the successful creation of the new analytical columns: `language_code` and `word_count`.

```
SELECT
  raw_message,
  language_code,
  sentiment_score,
  word_count
FROM
  `bigdata-elt-project.analytics_data.processed_logs`
ORDER BY
  processing_time DESC
LIMIT
  10;
```

| user_id   | raw_message                                                                                       | language_code | word_count | sentiment_score | main_topic     | processing_time                    |
|-----------|----------------------------------------------------------------------------------------------------|----------------|------------|-----------------|----------------|-------------------------------------|
|           | Everything was perfect and easy to use. Great experience!                                          | en             | 9          | 0.8111111111    | Other          | 2025-12-09 12:10:03.904046 UTC     |
| USER_1011 | Все быстро доставили! Отличная работа.                                                             | ru             | 5          |                 | general        | 2025-12-09 12:10:03.900721 UTC     |
| USER_1010 | The delivery was delayed, but the item itself is great. Mixed feelings.                            | en             | 12         | 0.4             | Delivery       | 2025-12-09 12:10:03.896655 UTC     |
| USER_1009 | The application is very buggy, it keeps crashing when I try to pay.                                | en             | 13         | 0.2             | Bug/Error      | 2025-12-09 12:10:03.892137 UTC     |
| USER_1008 | Everything was perfect and easy to use. Great experience!                                          | en             | 9          | 0.8111111111    | Other          | 2025-12-09 12:10:03.886897 UTC     |
| USER_1007 | The cost structure is unclear, and the monthly payment schedule seems excessive.                   | en             | 12         | -0.25           | Payment Issues | 2025-12-09 12:10:03.884109 UTC     |
| USER_1006 | Excellent service, I had no complaints at all about the customer support team.                     | en             | 13         | 1               | Other          | 2025-12-09 12:10:03.880899 UTC     |
| USER_1005 | My package hasn't arrived yet. The estimated speed was supposed to be quicker. Frustrating.        | en             | 14         | -0.4            | Delivery       | 2025-12-09 12:10:03.874016 UTC     |
| USER_1004 | This is an amazing new feature! Zero issues, everything just works.                                | en             | 11         | 0.3852272727    | Other          | 2025-12-09 12:10:03.870409 UTC     |
| USER_1003 | The price is too high for what you get. I'm disappointed with the final bill.                      | en             | 15         | -0.1966666667   | Payment Issues | 2025-12-09 12:10:03.865659 UTC     |
| USER_1002 | Delivery was super fast, arrived a day earlier than expected. Highly recommended!                  | en             | 12         | 0.1266666667    | Delivery       | 2025-12-09 12:10:03.862862 UTC     |
| USER_1001 | I love the quality of the product, but the checkout process was extremely slow and failed twice.   | en             | 17         | -0.1            | Bug/Error      | 2025-12-09 12:10:03.674827 UTC     |

### Fault Tolerance / Dead-Letter Queue (DLQ) Implementation

The pipeline was configured with a DLQ mechanism to ensure resilience against malformed input data. When a log line fails the initial parsing (e.g., incorrect separator or timestamp format), it is automatically rerouted:

* **Success Flow:** Continues to BigQuery.
* **Failure Flow (DLQ):** The failed record is captured, enriched with an error message, and written to GCS for later investigation.

**Verification of DLQ:**

The malformed test lines were successfully diverted and written to a JSON file in GCS:
* **GCS Path:** `gs://my-raw-data-pipeline-1985/dlq/malformed_logs.txt-*.json`
* **DLQ Content Example:**
```json
{"line": "2025-12-06 10:00      | USER_1012 | My package hasn't arrived yet...", "error": "Parsing error: Invalid isoformat string: '2025-12-06 10:00      '"}
```

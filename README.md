# GCP ELT Data Pipeline: Unstructured Log Analysis (Dataflow, GCS, BigQuery)

## 🌟 Project Overview

This project implements a robust Extract, Load, and Transform (ELT) pipeline on the Google Cloud Platform (GCP) to process unstructured user logs, perform sentiment analysis and topic extraction using Apache Beam, and load the clean, structured data into a data warehouse (BigQuery) for analytics.

This pipeline successfully transforms raw log messages into actionable metrics, providing insights into user feedback quality, delivery speed, and payment issues.

## ⚙️ Architecture

The pipeline leverages core GCP services for scalability and serverless processing.



| Component | Role |
| :--- | :--- |
| **Google Cloud Storage (GCS)** | Stores raw input data (`raw_logs.txt`) and serves as the staging/temp location for Dataflow. |
| **Apache Beam / Google Dataflow** | The serverless processing engine that runs the Python script. It handles orchestration, scaling, and the core ETL logic. |
| **Custom Beam Transforms** | Includes logic for parsing timestamps, extracting user IDs, calculating **Sentiment Score** (using `TextBlob`), and deriving the **Main Topic**. |
| **Google BigQuery** | The final data warehouse where processed logs are loaded into a structured schema for querying and visualization. |

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

```bash
python3 pipeline.py \
    --setup_file=./setup.py \
    --runner=DataflowRunner \
    --project=bigdata-elt-project \
    --region=us-central1 \
    --temp_location=gs://my-raw-data-pipeline-1985 /temp/ \
    --staging_location=gs://my-raw-data-pipeline-1985 /staging/
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

| raw_message                                                                                           | language_code | sentiment_score | word_count |
|--------------------------------------------------------------------------------------------------------|----------------|-----------------|------------|
| Все быстро доставили! Отличная работа.                                                                 | ru             |                 | 5          |
| The delivery was delayed, but the item itself is great. Mixed feelings.                                | en             | 0.4             | 12         |
| The application is very buggy, it keeps crashing when I try to pay.                                    | en             | 0.2             | 13         |
| Everything was perfect and easy to use. Great experience!                                              | en             | 0.8111111111    | 9          |
| The cost structure is unclear, and the monthly payment schedule seems excessive.                       | en             | -0.25           | 12         |
| Excellent service, I had no complaints at all about the customer support team.                         | en             | 1               | 13         |
| My package hasn't arrived yet. The estimated speed was supposed to be quicker. Frustrating.            | en             | -0.4            | 14         |
| This is an amazing new feature! Zero issues, everything just works.                                    | en             | 0.3852272727    | 11         |
| The price is too high for what you get. I'm disappointed with the final bill.                          | en             | -0.1966666667   | 15         |
| Delivery was super fast, arrived a day earlier than expected. Highly recommended!                      | en             | 0.1266666667    | 12         |

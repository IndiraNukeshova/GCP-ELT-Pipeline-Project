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
    gcloud config set project [YOUR_PROJECT_ID]
    ```
3.  **Virtual Environment (venv)**: Activated and required packages installed.
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 How to Run the Pipeline

The pipeline is submitted to the Dataflow service using the command line, referencing the external dependency file (`setup.py`).

### 1. Setup Data and Dependencies

* **GCS Bucket:** Ensure your bucket, `gs://[YOUR_BUCKET_NAME]`, is created, and the folders `/staging/` and `/temp/` exist.
* **Input File:** Upload the raw data file to GCS:
    ```bash
    gsutil cp raw_logs.txt gs://[YOUR_BUCKET_NAME]/raw_logs.txt
    ```

### 2. Execute Dataflow Job

Execute the pipeline from your project directory:

```bash
python3 pipeline.py \
    --setup_file=./setup.py \
    --runner=DataflowRunner \
    --project=[YOUR_PROJECT_ID] \
    --region=[YOUR_REGION] \
    --temp_location=gs://[YOUR_BUCKET_NAME]/temp/ \
    --staging_location=gs://[YOUR_BUCKET_NAME]/staging/

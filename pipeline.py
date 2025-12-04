import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions, StandardOptions, WorkerOptions
import re
import datetime
import logging
from textblob import TextBlob

# ----------------- PROJECT CONFIGURATION -----------------
PROJECT_ID = 'bigdata-elt-project'
BUCKET_NAME = 'my-raw-data-pipeline-1985'
REGION = 'us-central1'
INPUT_FILE = f'gs://{BUCKET_NAME}/raw_logs.txt'
OUTPUT_TABLE = f'{PROJECT_ID}:analytics_data.processed_logs'


# --------- TRANSFORMATION FUNCTIONS (T - Transform) ----------
class ParseLogLine(beam.DoFn):
    """
    Извлекает структурированные поля из неструктурированной строки лога.
    """
    def process(self, element):
        try:
            parts = element.split(' | ', 2)
            if len(parts) != 3:
                logging.warning(f"Skipping malformed line: {element}")
                return

            timestamp_str, user_id, raw_message = parts

            # Parsing time (TIMESTAMP)
            log_timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # Pass to the next function for NLP analysis
            yield {
                'log_timestamp': log_timestamp,
                'user_id': user_id,
                'raw_message': raw_message
            }
        except Exception as e:
            logging.error(f"Error parsing line {element}: {e}")
            pass


class AnalyzeText(beam.DoFn):
    def process(self, element):
        message = element['raw_message']

        # 1. Sentiment Analysis
        blob = TextBlob(message)
        sentiment_score = blob.sentiment.polarity

        # 2. Topic Modeling (Simplified Example)
        main_topic = 'Other'
        if re.search(r'payment|bill|price|cost', message, re.IGNORECASE):
            main_topic = 'Payment Issues'
        elif re.search(r'delivery|speed|arrive|fast', message, re.IGNORECASE):
            main_topic = 'Delivery'

        # 3. Adding the extracted fields to our object
        element['sentiment_score'] = float(sentiment_score) # FLOAT
        element['main_topic'] = main_topic # STRING
        element['processing_time'] = datetime.datetime.now(datetime.timezone.utc).isoformat() # TIMESTAMP

        # 4. Check that all types comply with the BigQuery schema.
        element['log_timestamp'] = element['log_timestamp'].isoformat() 

        yield element


# ----------------- CONVEYOR BASIC LOGIC -----------------
def run_pipeline():
    options = PipelineOptions()
    options.view_as(StandardOptions).runner = 'DataflowRunner'

    google_cloud_options = options.view_as(GoogleCloudOptions)
    google_cloud_options.project = PROJECT_ID
    google_cloud_options.region = REGION

    google_cloud_options.temp_location = f'gs://{BUCKET_NAME}/temp/'

    with beam.Pipeline(options=options) as p:

        (p
         # 1. READ
         | 'ReadRawData' >> beam.io.ReadFromText(INPUT_FILE)

         # 2. TRANSFORM (T1)
         | 'ParseLogFields' >> beam.ParDo(ParseLogLine())

         # 3. TRANSFORM (T2): NLP/ML
         | 'AnalyzeAndEnrich' >> beam.ParDo(AnalyzeText())

         # 4. LOAD
         | 'WriteToBigQuery' >> beam.io.WriteToBigQuery(
             table=OUTPUT_TABLE,
             create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
         )
        )


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    print("Запуск Dataflow конвейера...")
    run_pipeline()

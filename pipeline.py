import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions, StandardOptions, WorkerOptions
import re
import datetime
import logging
from textblob import TextBlob
from langdetect import detect
import json

# ----------------- PROJECT CONFIGURATION -----------------
PROJECT_ID = 'bigdata-elt-project'
BUCKET_NAME = 'my-raw-data-pipeline-1985'
REGION = 'us-central1'
INPUT_FILE = f'gs://{BUCKET_NAME}/raw_logs.txt'
OUTPUT_TABLE = f'{PROJECT_ID}:analytics_data.processed_logs'


# ----------------- BIGQUERY SCHEMA DEFINITION -----------------
def get_bigquery_schema():
    """Defines the explicit schema for the processed_logs table."""
    return {
        'fields': [
            {'name': 'log_timestamp', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
            {'name': 'user_id', 'type': 'STRING', 'mode': 'REQUIRED'},
            {'name': 'raw_message', 'type': 'STRING', 'mode': 'REQUIRED'},

            # Fields created in the initial pipeline
            {'name': 'sentiment_score', 'type': 'FLOAT', 'mode': 'NULLABLE'},
            {'name': 'main_topic', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'processing_time', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},

            # Fields for Advanced Analysis
            {'name': 'language_code', 'type': 'STRING', 'mode': 'REQUIRED'},
            {'name': 'word_count', 'type': 'INTEGER', 'mode': 'REQUIRED'}
        ]
    }


# ----------------- TAGS FOR DLQ -----------------
SUCCESS_TAG = 'success'
DLQ_TAG = 'dlq'


# --------- TRANSFORMATION FUNCTIONS (T - Transform) ----------
class ParseLogLine(beam.DoFn):
    """
    Extracts structured fields from an unstructured log line
    and routes erroneous lines to the DLQ.
    """
    def process(self, element):
        try:
            parts = element.split(' | ', 2)

            # 1. Format validation
            if len(parts) != 3:
                error_output = {'line': element, 'error': 'Malformed line format (not 3 parts)'}
                yield beam.pvalue.TaggedOutput(DLQ_TAG, error_output)
                return

            timestamp_str, user_id, raw_message = parts

            # 2. Time parsing (will raise Exception on invalid format)
            log_timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # 3. Successful output -> SUCCESS_TAG
            yield beam.pvalue.TaggedOutput(SUCCESS_TAG, {
                'log_timestamp': log_timestamp,
                'user_id': user_id,
                'raw_message': raw_message
            })

        except Exception as e:
            # 4. Parsing error -> DLQ_TAG
            error_output = {
                'line': element, 
                'error': f'Parsing error: {e}',
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            yield beam.pvalue.TaggedOutput(DLQ_TAG, error_output)


class AnalyzeText(beam.DoFn):
    """Performs advanced NLP analysis and data enrichment."""
    def process(self, element):
        message = element['raw_message']

        # 1. Word Count
        word_count = len(message.split())
        element['word_count'] = word_count

        # 2. Language Detection
        try:
            # langdetect often requires the string to be long enough
            lang_code = detect(message)
        except:
            lang_code = 'unknown' 

        element['language_code'] = lang_code

        # Initialize analytical fields
        sentiment_score = None
        main_topic = 'general'

        # 3. Sentiment and Topic Analysis (only for English)
        if lang_code == 'en':
            try:
                blob = TextBlob(message)
                sentiment_score = blob.sentiment.polarity

                # Simple Topic Extraction Logic
                message_lower = message.lower()

                if re.search(r'delivery|package|arrived|speed', message_lower):
                    main_topic = 'Delivery'
                elif re.search(r'payment|fee|invoice|bill|price', message_lower):
                    main_topic = 'Payment Issues'
                elif re.search(r'error|bug|crash|fail', message_lower):
                    main_topic = 'Bug/Error'
                else:
                    main_topic = 'Other'

            except Exception as e:
                sentiment_score = None
                main_topic = 'NLP_Error'

        # Update element
        element['sentiment_score'] = sentiment_score
        element['main_topic'] = main_topic
        element['processing_time'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
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

    # OUTPUT LOCATION FOR DLQ
    DLQ_OUTPUT_PATH = f'gs://{BUCKET_NAME}/dlq/malformed_logs.txt'

    with beam.Pipeline(options=options) as p:

        # 1. READ
        main_data = p | 'ReadRawData' >> beam.io.ReadFromText(INPUT_FILE)

        # 2. TRANSFORM (T1) - Split data into 2 PCollections
        parsed_data = (
            main_data 
            | 'ParseAndRoute' >> beam.ParDo(ParseLogLine()).with_outputs(
                SUCCESS_TAG, DLQ_TAG)
        )

        # 3. Success stream (SUCCESS_TAG) - continue ELT
        (parsed_data[SUCCESS_TAG]

         # 4. TRANSFORM (T2): NLP/ML
         | 'AnalyzeAndEnrich' >> beam.ParDo(AnalyzeText())

         # 5. LOAD Clean Data
         | 'WriteToBigQuery' >> beam.io.WriteToBigQuery(
             table=OUTPUT_TABLE,
             schema=get_bigquery_schema(),
             create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
         )
        )

        # 6. Error stream (DLQ_TAG) - Write to GCS
        (parsed_data[DLQ_TAG]
         | 'FormatDLQ' >> beam.Map(lambda x: json.dumps(x)) # Convert DLQ dict to JSON string
         | 'WriteDLQToGCS' >> beam.io.WriteToText(
             file_path_prefix=DLQ_OUTPUT_PATH,
             file_name_suffix='.json',
         )
        )


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    print("Starting Dataflow pipeline...")
    run_pipeline()

import setuptools

setuptools.setup(
    name='bigdata-elt-pipeline',
    version='1.0.0',
    install_requires=[
        'apache-beam[gcp]',
        'google-cloud-bigquery',
        'TextBlob',
        'numpy',
        'langdetect'
    ],
    packages=setuptools.find_packages(),
    description='Dataflow pipeline for unstructured data processing and sentiment analysis.',
)

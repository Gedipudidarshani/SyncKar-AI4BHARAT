from confluent_kafka import Producer
import sys

conf = {
    'bootstrap.servers': 'kafka-2a1a1df2-senthankarnala-e159.j.aivencloud.com:26119',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'PLAIN',
    'sasl.username': 'avnadmin',
    'sasl.password': 'AVNS__unsvgQm2UzIXpbJTfG',
    'enable.ssl.certificate.verification': False
}

try:
    p = Producer(conf)
    metadata = p.list_topics(timeout=10)
    print("SUCCESS with PLAIN!")
    print("Topics:", metadata.topics.keys())
    sys.exit(0)
except Exception as e:
    print("Failed with PLAIN:", e)
    

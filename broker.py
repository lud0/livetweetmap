import pika

broker_exchange = 'tweets_exchange'


def init_broker_channel():
    print("Initializing broker exchange: %s" % broker_exchange)

    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange=broker_exchange,
                             exchange_type='direct')
    return channel

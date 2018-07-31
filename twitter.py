import json
import os
import random
import threading
import time

import tweepy

import broker

tw_auth = None


def init_tweepy():
    # Initialize Tweepy auth
    global tw_auth

    print("Initializing Tweepy auth")
    consumer_key = os.getenv('TW_CONSUMER_KEY', None)
    consumer_secret = os.getenv('TW_CONSUMER_SECRET', None)
    access_token = os.getenv('TW_ACCESS_TOKEN', None)
    access_token_secret = os.getenv('TW_ACCESS_TOKEN_SECRET', None)
    tw_auth = tweepy.auth.OAuthHandler(consumer_key, consumer_secret)
    tw_auth.set_access_token(access_token, access_token_secret)


class TweetStreamListener(tweepy.StreamListener):

    def __init__(self, routing_key, *args, **kwargs):
        super(TweetStreamListener, self).__init__(*args, **kwargs)
        self.routing_key = routing_key
        self.broker_channel = broker.init_broker_channel()

    def on_data(self, data):
        """
        callback whenever a new tweet arrives: push it to the broker
        """
        json_data = json.loads(data)

        coords = json_data["coordinates"]
        if coords is not None:
            lng = coords["coordinates"][0]
            lat = coords["coordinates"][1]
            tweet = json_data["text"]
            cleaned_data = json.dumps({'tweet': tweet, 'lat': lat, 'lng': lng})
            self.broker_channel.basic_publish(exchange=broker.broker_exchange, routing_key=self.routing_key, body=cleaned_data)

    def on_error(self, status_code):
        # TODO implement error handling, when to reconnect etc..
        # see: https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/connecting
        # print(status_code)
        # return True  # keep stream alive
        return False  # kill stream


class FakeTwitterStreamThread(threading.Thread):
    """
    Class that emulates a real twitter stream by sending a geo tweet at random interval
    """

    def __init__(self, routing_key, location, *args, **kwargs):
        super(FakeTwitterStreamThread, self).__init__(*args, **kwargs)
        self.routing_key = routing_key
        self.location = location
        self.shutdown_flag = threading.Event()

    def run(self):
        """
        Infinite loop that generates fake tweets and pushes them to the broker
        """
        broker_channel = broker.init_broker_channel()

        print("Starting Twitter Stream Thread: %s" % self.routing_key)
        while not self.shutdown_flag.is_set():
            tweet = 'Tweet {0}: {1}'.format(random.randint(1, 100), int(time.time()))
            lng = random.uniform(self.location['sw']['lng'], self.location['ne']['lng'])
            lat = random.uniform(self.location['sw']['lat'], self.location['ne']['lat'])

            cleaned_data = json.dumps({'tweet': tweet, 'lat': lat, 'lng': lng})

            broker_channel.basic_publish(exchange=broker.broker_exchange, routing_key=self.routing_key, body=cleaned_data)
            time.sleep(10+random.randint(0, 3))

        print("Exiting Twitter Stream Thread: %s" % self.routing_key)

    def close(self):
        self.shutdown_flag.set()

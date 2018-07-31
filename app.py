import json
import os
import time

import tweepy
from flask import Flask, render_template, request
from flask_socketio import SocketIO

import broker
import twitter

########################################################################################################################
# run the server in debug mode or not
debug = False

# in case of not having Twitter credentials, setting to True will generate some fake tweets to prove the concept
debug_use_fake_twitter = True

google_api_key = os.getenv('GOOGLE_API_KEY', None)
initial_map_location = {'sw': {'lng': -74, 'lat': 40},
                        'ne': {'lng': -73, 'lat': 41}}
########################################################################################################################

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret1234'
socketio = SocketIO(app, async_mode='threading')

user_streams = {}


class UserStream:

    def __init__(self, ws_id, location):
        self.ws_id = ws_id
        self.tw_stream = None
        self.location = location

        # starts the thread responsible for consuming the tweets from the broker and pushing them
        # to the client via web socket
        socketio.start_background_task(target=self.consume_and_forward)

        # start the tweet stream thread that will push new tweets for my location on the broker tweets queue
        self.start_tweet_stream()

    def start_tweet_stream(self):
        """
        Starts a new tweet stream for the current self.location
        """
        print('Starting Tweet Stream Listener for location: %s' % self.location)

        if not debug_use_fake_twitter:
            # use the real twitter stream
            tw_stream = tweepy.Stream(auth=twitter.tw_auth,
                                      listener=twitter.TweetStreamListener(routing_key=self.ws_id),
                                      timeout=90)
            tw_stream.filter(locations=self.get_location_twitter_format, async=True)
        else:
            # use a fake twitter stream
            tw_stream = twitter.FakeTwitterStreamThread(routing_key=self.ws_id, location=self.location)
            tw_stream.setDaemon(True)
            tw_stream.start()
        self.tw_stream = tw_stream

    def close_tweet_stream(self):
        """
        Close the current Tweet stream self.tw_stream
        """
        if self.tw_stream:
            print('Closing Tweet Stream Listener')
            self.tw_stream.close()

    def consume_and_forward(self):
        """
        Thread that consumes the tweets from the broker queue and sends them to the client via web socket
        """

        channel = broker.init_broker_channel()
        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange=broker.broker_exchange,
                           queue=queue_name,
                           routing_key=self.ws_id)

        # starts the infinte loop that consumes the broker queue with the tweets and
        # emits them over the web socket to the client
        # NB: only emits to the correct client: the room identified by its ws_id
        while True:
            method, prop, body = channel.basic_get(queue=queue_name)
            if body:
                data = json.loads(body)
                tweet = data['tweet']
                lat = data['lat']
                lng = data['lng']
                socketio.emit('new_tweet', {'tweet': tweet, 'lat': lat, 'lng': lng}, room=self.ws_id)
            else:
                time.sleep(0.5)

    def update_location(self, latitude=None, longitude=None, sw_bound=None, ne_bound=None):
        """
        Location has changed: stop the current tweet stream and restart on the new location
        """
        self.close_tweet_stream()
        if sw_bound is not None and ne_bound is not None:
            self.location = {'sw': {'lng': float(sw_bound['lng']), 'lat': float(sw_bound['lat'])},
                             'ne': {'lng': float(ne_bound['lng']), 'lat': float(ne_bound['lat'])}}

        elif latitude and longitude:
            self.location = {'sw': {'lng': float(longitude-0.5), 'lat': float(latitude-0.5)},
                             'ne': {'lng': float(longitude+0.5), 'lat': float(latitude+0.5)}}
        self.start_tweet_stream()

    @property
    def get_location_twitter_format(self):
        """
        returns an array: [ sw.lng, sw.lat, ne.lng, ne.lat]
        https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters.html
        bounding box should be specified as a pair of longitude and latitude pairs,
        with the southwest corner of the bounding box coming first.
        [-122.75,36.8,-121.75,37.8]	San Francisco
        [-74,40,-73,41]	New York City
        """
        return [self.location['sw']['lng'], self.location['sw']['lat'],
                self.location['ne']['lng'], self.location['ne']['lat']]


@app.route('/')
def index():
    """
    Serve the web page
    """
    context = {'GOOGLE_API_KEY': google_api_key,
               'sw': initial_map_location['sw'],
               'ne': initial_map_location['ne']}

    return render_template('index.html', async_mode=socketio.async_mode, context=context)


@socketio.on('connect')
def ws_connect():
    """
    Upon connecting the web socket, instantiate a new UserStream
    """
    print("WS connect: %s" % request.sid)
    global user_streams

    if request.sid not in user_streams:
        user = UserStream(ws_id=request.sid, location=initial_map_location)
        user_streams[request.sid] = user
        socketio.emit('connected', {'ws_id': request.sid, 
                                    'sw': initial_map_location['sw'],
                                    'ne': initial_map_location['ne']}, room=request.sid)
        print("New user: %s" % user_streams)


@socketio.on('disconnect')
def ws_disconnect():
    print("WS disconnect: %s" % request.sid)
    user = user_streams.pop(request.sid, None)
    if user:
        user.close_tweet_stream()


@socketio.on('submit_bounds')
def ws_bounds(data):
    """
    User changed map bounds
    """
    print("WS bounds: %r" % data)
    user = user_streams[request.sid]
    user.update_location(sw_bound=data.get('sw', None), ne_bound=data.get('ne', None))


if __name__ == '__main__':
    if not debug_use_fake_twitter:
        twitter.init_tweepy()
    socketio.run(app, debug=debug)

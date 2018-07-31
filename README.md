# LiveTweetMap

Web page showing the stream of live Geo Tweets coming in and marked on a map.


## Tech stack overview

- Flask / Python 3
- RabbitMQ
- SocketIO
- Tweepy
- Javascript / jQuery / Bootstrap
- Google Maps API

## Setup

Steps needed to get it up and running:

1. head over to https://developer.twitter.com and register to have your API keys
2. head over to https://cloud.google.com/maps-platform/ and get your API KEY
3. edit the `secrets.env` file and set them:
**GOOGLE_API_KEY**, **TW_CONSUMER_KEY**, **TW_CONSUMER_SECRET**,
**TW_ACCESS_TOKEN**, **TW_ACCESS_TOKEN_SECRET**

4. install rabbitmq broker: https://www.rabbitmq.com/download.html
5. open a shell and run it with `rabbitmq-server`
6. prepare the environment and run the server:
```
virtualenv .ve -p python3
source .ve/bin/activate && source secrets.env
pip install -r requirements.txt
python3 app.py
```
7. point your browser to http://localhost:5000/ and play around!

## How it works

When a client connects to the web server, a new web socket connection is created and a UserStream is instantiated
identified by the web socket ID: `ws_id`.

In turn, the `userstream` instance spawns 2 threads:
1. a Tweepy twitter live stream listener: filtering only geo tweets whose coordinates fall within a
defined geographic region and pushes them in a ws_id-identified RabbitMQ queue
2. a queue consumer that listens to the ws_id-identified RabbitMQ queue, pops any tweet present and emits them
via web socket to the client

On the client side, whenever a new tweet event is received via web socket, it is added to the list of tweets and
added on the map as a marker using Google Maps API and some JS/jQuery magic.
Only the most recent tweets are shown, older gets deleted from the list on a rolling basis.

When the user changes the geographic region, either by dragging/zooming the map or by setting the center coordinates,
an event is sent via web socket to the server. The server restarts thread 1. since the twitter geographic
filter has changed.

## What if I don't have a Twitter API keys ?

Fear not, you can still try the concept by setting `debug_use_fake_twitter = True` in `app.py`.
In such case, a fake Twitter stream is generated, randomly throwing boring tweets.


## Disclaimer

The real geo twitter stream hasn't been debugged/checked since I don't have Twitter credentials yet (pending approval).


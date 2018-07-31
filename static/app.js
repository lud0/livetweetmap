var map;
var socket;
var markers = [];
var tweet_count = 0;
var max_tweets = 5;

function initMap() {
    // Callback on google Map initialization
    var sw = new google.maps.LatLng(init_sw.lat, init_sw.lng);
    var ne = new google.maps.LatLng(init_ne.lat, init_ne.lng);

    // Create the map object: fix the zoom range and center with the initial bounds
    map = new google.maps.Map(document.getElementById('map'), {
      bounds: new google.maps.LatLngBounds(sw, ne),
      minZoom: 7,
      maxZoom: 12,
    });

    // Add event listener when map returned idle after some changes (e.g. zoom/drag)
    map.addListener('idle', function() {sendNewBounds();});
}

function setFormCoordinates(sw, ne) {
    // Updates the center coordinates in the form
    var lat_center = (ne['lat']() + sw['lat']()) / 2.;
    var lon_center = (ne['lng']() + sw['lng']()) / 2.;
    $('input[name="latitude"]').val(lat_center);
    $('input[name="longitude"]').val(lon_center);
}

function sendNewBounds() {
    // When map changed, update the center coordinates in the form, clear the markers and
    // send the new bounds to the backend so the geo tweet stream can be updated
    var bounds =  map.getBounds();
    var ne = bounds.getNorthEast();
    var sw = bounds.getSouthWest();
    setFormCoordinates(sw, ne);

    clearMarkers();
    $('#log').empty();
    tweet_count = 0;
    socket.emit('submit_bounds', {ne: ne, sw: sw});
}

function setMapOnAll(map) {
    // Sets the map on all markers in the array.
    for (var i = 0; i < markers.length; i++) {
        markers[i].setMap(map);
    }
}

function clearMarkers() {
    // Removes the markers from the map, but keeps them in the array.
    setMapOnAll(null);
}

$(document).ready(function() {
    var namespace = '';
    socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + namespace);

    // Event handler for server sent data
    socket.on('connected', function(msg) {
        $('#intro').text(msg.ws_id);
        var sw = new google.maps.LatLng(msg.sw.lat, msg.sw.lng);
        var ne = new google.maps.LatLng(msg.ne.lat, msg.ne.lng);
        map.fitBounds(new google.maps.LatLngBounds(sw, ne));
        setFormCoordinates(sw, ne);
    });

    // New tweet arrives, update list and add marker
    socket.on('new_tweet', function(msg) {
        if (tweet_count>=max_tweets) {
            $('#log li:last-child').remove();
        } else {
            tweet_count += 1;
        }
        $('#log').prepend('<li class="list-group-item">' + msg.tweet + '</li>');

        marker = new google.maps.Marker({
            position: new google.maps.LatLng(msg.lat, msg.lng),
            map: map
        });
        markers.push(marker);
    });

    // Handler for the form submit button: recenter the map, which in turn will trigger the 'idle' event
    $('form#emit').submit(function(event) {
        var lat = $(this).find('input[name="latitude"]').val();
        var lng = $(this).find('input[name="longitude"]').val();
        map.setCenter(new google.maps.LatLng(lat, lng));
        return false;
    });
});

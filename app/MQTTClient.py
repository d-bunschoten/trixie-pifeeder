import paho.mqtt.client as mqtt
import json
import socket
import time
import logging
import threading

logger = logging.getLogger(__name__)

TOPIC_PREFIX = "cat_feeder"
DEFAULT_PORTIONS = 1
MAX_PORTIONS = 5

class MQTTClient:
    def __init__(self, config, callbacks):
        mqtt_config = config.mqtt
        device_config = config.device

        self.mqtt_host = mqtt_config.get("host")
        self.mqtt_user = mqtt_config.get("user")
        self.mqtt_pass = mqtt_config.get("pass")
        self.feeder_id = device_config.get("id")
        self.name = device_config.get("name")
        self.config_url = device_config.get("config_url")
        self.connected = False

        self.feeding_callback = callbacks.get("feeding_callback")
        self.status_callback = callbacks.get("status_callback")
        self.update_callback = callbacks.get("update_callback")
        self.displaytest_callback = callbacks.get("displaytest_callback")

        self.client = mqtt.Client()
        self.client.username_pw_set(self.mqtt_user, self.mqtt_pass)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self.connection_lock = threading.Lock()
        self._stop_event = threading.Event()

    def connect(self):
        with self.connection_lock:
            if not self.connected and (not hasattr(self, '_connection_thread') or not self._connection_thread.is_alive()):
                self._connection_thread = threading.Thread(target=self._connect_loop, daemon=True)
                self._connection_thread.start()

    def _connect_loop(self):
        while not self._stop_event.is_set() and not self.connected:
            try:
                logger.debug(f"Connecting to MQTT host {self.mqtt_host}...")
                self.client.connect(self.mqtt_host, 1883, 10)
                self.client.loop_start()
                self.connected = True  # Only set this if connection was successful
            except (ConnectionRefusedError, socket.gaierror) as e:
                logger.warning("Failed to connect. Trying again in 20 seconds.")
                for _ in range(20):  # Split 20 sec into twenty 1-sec sleeps
                    time.sleep(1)  # Sleep for 1 sec
                    if self._stop_event.is_set():
                        return

    def disconnect(self):
        if hasattr(self, '_connection_thread') and self._connection_thread.is_alive():
            self._stop_event.set()  # Send stop signal to the connect thread
            self._connection_thread.join()  # Wait for _connect_loop to finish
            self._stop_event = threading.Event()
        if self.connected:
            self.connected = False
            self.client.loop_stop()
            self.client.disconnect()

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection. Trying to reconnect...")

    def _on_connect(self, client, userdata, flags, rc):
        logger.debug(f"Connected to MQTT '{self.mqtt_host}'. Subscribing to topics")
        feed_topic = f"{TOPIC_PREFIX}/{self.feeder_id}/feed"
        status_request_topic = f"{TOPIC_PREFIX}/{self.feeder_id}/status_request"
        update_topic = f"{TOPIC_PREFIX}/{self.feeder_id}/update"
        displaytest_topic = f"{TOPIC_PREFIX}/{self.feeder_id}/displaytest"
        discovery_topic = f"{TOPIC_PREFIX}/discovery"

        self.client.subscribe(feed_topic)
        self.client.subscribe(status_request_topic)
        self.client.subscribe(update_topic)
        self.client.subscribe(displaytest_topic)
        self.client.subscribe(discovery_topic)

        self.send_status_message()

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())

            if topic.endswith("/feed"):
                logger.debug("MQTT feed command was received")
                portions = payload.get("portions", DEFAULT_PORTIONS)
                if(portions > MAX_PORTIONS):
                    portions = MAX_PORTIONS
                if self.feeding_callback:
                    self.feeding_callback(portions)

            elif topic.endswith("/status_request"):
                logger.debug("MQTT status request command was received")
                self.send_status_message()

            elif topic.endswith("/displaytest"):
                logger.debug(f"MQTT displattest command received")
                method = payload.get("method")
                params = payload.get("params", [])
                paramstring = ",".join([str(p) for p in params])
                if method != None:
                    logger.debug(f"Send display signal: {method} ({paramstring})")
                    self.displaytest_callback(method, params)
                else:
                    logger.warning(f"Invalid display signal: {method} ({paramstring})")

    #        elif topic.endswith("/update"):
    #            logger.debug("MQTT update was received")
    #            if self.update_callback:
    #                self.update_callback(payload)

            elif topic == f"{TOPIC_PREFIX}/discovery":
                logger.debug("MQTT discovery command was received")
                self.send_discovery_response()
        except Exception:
            logger.warning("An invalid MQTT command was sent")

    def send_status_message(self):
        topic = f"{TOPIC_PREFIX}/{self.feeder_id}/status"
        if self.connected and self.status_callback:
            status = self.status_callback()
            self.client.publish(topic, json.dumps(status))

    def send_discovery_response(self):
        if self.connected:
            topic = f"{TOPIC_PREFIX}/discovery_response"
            payload = {
                "feeder_id": self.feeder_id,
                "name": self.name,
                "config_url": self.config_url
            }
            self.client.publish(topic, json.dumps(payload))
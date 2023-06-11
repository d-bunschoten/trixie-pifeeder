import paho.mqtt.client as mqtt
import json

import logging

logger = logging.getLogger()

TOPIC_PREFIX = "cat_feeder"
DEFAULT_PORTIONS = 1

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

        self.feeding_callback = callbacks.get("feeding_callback")
        self.status_callback = callbacks.get("status_callback")
        self.update_callback = callbacks.get("update_callback")

        self.client = mqtt.Client()
        self.client.username_pw_set(self.mqtt_user, self.mqtt_pass)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def connect(self):
        logger.debug(f"Connecting to MQTT host {self.mqtt_host}...")
        self.client.connect(self.mqtt_host, 1883, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        logger.debug(f"Connected to MQTT '{self.mqtt_host}'! Subscribing to topics...")
        feed_topic = f"{TOPIC_PREFIX}/{self.feeder_id}/feed"
        status_request_topic = f"{TOPIC_PREFIX}/{self.feeder_id}/status_request"
        update_topic = f"{TOPIC_PREFIX}/{self.feeder_id}/update"
        discovery_topic = f"{TOPIC_PREFIX}/discovery"

        self.client.subscribe(feed_topic)
        self.client.subscribe(status_request_topic)
        self.client.subscribe(update_topic)
        self.client.subscribe(discovery_topic)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = json.loads(msg.payload.decode())

        if topic.endswith("/feed"):
            portions = payload.get("portions", DEFAULT_PORTIONS)
            if self.feeding_callback:
                self.feeding_callback(portions)

        elif topic.endswith("/status_request"):
            self.send_status_message()

        elif topic.endswith("/update"):
            if self.update_callback:
                self.update_callback(payload)

        elif topic == f"{TOPIC_PREFIX}/discovery":
            self.send_discovery_response()

    def send_status_message(self):
        topic = f"{TOPIC_PREFIX}/{self.feeder_id}/status"
        if self.status_callback:
            status = self.status_callback()
            self.client.publish(topic, json.dumps(status))

    def send_discovery_response(self):
        topic = f"{TOPIC_PREFIX}/discovery_response"
        payload = {
            "feeder_id": self.feeder_id,
            "name": self.name,
            "config_url": self.config_url
        }
        self.client.publish(topic, json.dumps(payload))
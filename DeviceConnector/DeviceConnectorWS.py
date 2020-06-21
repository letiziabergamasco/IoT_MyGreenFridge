# ----------------------------------------------------------------------
# Author: Letizia Bergamasco
# 
# Description: Raspberry Pi Connector, implementing a Device Connector,
#   which integrates the Raspberry Pi board into the platform.
#   - MQTT publisher on topics:
#       > MyGreenFridge/<userID>/<fridgeID>/temperature
#       > MyGreenFridge/<userID>/<fridgeID>/humidity
#       > MyGreenFridge/<userID>/<fridgeID>/camera0
#       > MyGreenFridge/<userID>/<fridgeID>/camera1
# ----------------------------------------------------------------------


from DeviceConnector import *
import cherrypy
import json
import socket
import paho.mqtt.client as PahoMQTT
import threading
import requests
import sys
import time

class DeviceConnectorMQTT:

	def __init__(self, clientID, broker, port, deviceConnector):

		self.broker = broker
		self.port = port
		self.clientID = clientID

		self._topic = ""
		self._isSubscriber = False

		# create an instance of paho.mqtt.client
		self._paho_mqtt = PahoMQTT.Client(clientID, False) 

		# register the callback
		self._paho_mqtt.on_connect = self.myOnConnect
		self._paho_mqtt.on_message = self.myOnMessageReceived



	def myOnConnect (self, paho_mqtt, userdata, flags, rc):
		print ("Connected to broker: " + str(self.broker) + ", with result code: " + str(rc))

	def myOnMessageReceived (self, paho_mqtt , userdata, msg):
		# A new message is received
		#self.notifier.notify (msg.topic, msg.payload)
		#print("Message received: " + str(msg.payload))
		#print("On topic: ", str(msg.topic))
		print("Message received on topic: ", str(msg.topic))


	def myPublish (self, topic, msg):
		# if needed, you can do some computation or error-check before publishing
		#print ("Publishing message: " + str(msg))
		#print("with topic: " + str(topic))
		print("Publishing message with topic: " + str(topic))
		# publish a message with a certain topic
		self._paho_mqtt.publish(topic, msg, 2)

	def mySubscribe (self, topic):
		# if needed, you can do some computation or error-check before subscribing
		print ("Subscribing to topic: " +str(topic))
		# subscribe for a topic
		self._paho_mqtt.subscribe(topic, 2)

		# just to remember that it works also as a subscriber
		self._isSubscriber = True
		self._topic = topic

	def start(self):
		#manage connection to broker
		self._paho_mqtt.connect(self.broker , self.port)
		self._paho_mqtt.loop_start()

	def stop (self):
		if (self._isSubscriber):
			# remember to unsuscribe if it is working also as subscriber
			self._paho_mqtt.unsubscribe(self._topic)

		self._paho_mqtt.loop_stop()
		self._paho_mqtt.disconnect()

class TemperatureThread(threading.Thread):

		def __init__(self, deviceConnector, deviceConnectorMQTT):
			threading.Thread.__init__(self)

		def run(self):
			while True:
				try:
					Tsenml = deviceConnector.get_temperature()
					msg = json.dumps(Tsenml)
				except:
					print("Error in retrieving temperature value.")
				topic = "MyGreenFridge/"+str(deviceConnector.userID)+"/"+str(deviceConnector.fridgeID)+"/temperature"
				deviceConnectorMQTT.myPublish(topic, msg)
				time.sleep(15)

class HumidityThread(threading.Thread):

		def __init__(self, deviceConnector, deviceConnectorMQTT):
			threading.Thread.__init__(self)

		def run(self):
			while True:
				try:
					Hsenml = deviceConnector.get_humidity()
					msg = json.dumps(Hsenml)
				except:
					print("Error in retrieving humidity value.")
				topic = "MyGreenFridge/"+str(deviceConnector.userID)+"/"+str(deviceConnector.fridgeID)+"/humidity"
				deviceConnectorMQTT.myPublish(topic, msg)
				time.sleep(15)

class Camera0Thread(threading.Thread):

		def __init__(self, deviceConnector, deviceConnectorMQTT):
			threading.Thread.__init__(self)

		def run(self):
			while True:
				try:
					C0senml = deviceConnector.get_camera0()
					msg = json.dumps(C0senml)
				except:
					print("Error in retrieving camera0 value.")
				topic = "MyGreenFridge/"+str(deviceConnector.userID)+"/"+str(deviceConnector.fridgeID)+"/camera0"
				deviceConnectorMQTT.myPublish(topic, msg)
				time.sleep(10)

class Camera1Thread(threading.Thread):

		def __init__(self, deviceConnector, deviceConnectorMQTT):
			threading.Thread.__init__(self)

		def run(self):
			while True:
				try:
					C1senml = deviceConnector.get_camera1()
					msg = json.dumps(C1senml)
				except:
					print("Error in retrieving camera1 value.")
				topic = "MyGreenFridge/"+str(deviceConnector.userID)+"/"+str(deviceConnector.fridgeID)+"/camera1"
				deviceConnectorMQTT.myPublish(topic, msg)
				time.sleep(10)

class RegistrationThread(threading.Thread):

		def __init__(self, deviceConnector, catalogIP, catalogPort):
			threading.Thread.__init__(self)

		def run(self):
			
			url = "http://"+ catalogIP + ":"+ catalogPort + "/"
			
			while True:

				### register fridge on the Catalog

				dictFridge = {"ID": deviceConnector.fridgeID,
							  "sensors":[]}
				jsonFridge = json.dumps(dictFridge)
				r2 = requests.put(url+"update_fridge", data=jsonFridge)

				### register sensors in the fridge on the Catalog

				##### temperature sensor
				Tsenml = deviceConnector.get_temperature()
				Tval = ((Tsenml['e'])[0])['v']
				dictTemp = {"sensor_ID": deviceConnector.temperatureID,
							"Value": Tval}
				jsonTemp = json.dumps(dictTemp)
				r3 = requests.post(url+"add_sensor?Fridge_ID=" + deviceConnector.fridgeID, data=jsonTemp)

				##### humidity sensor
				Hsenml = deviceConnector.get_humidity()
				Hval = ((Hsenml['e'])[0])['v']
				dictHum = {"sensor_ID": deviceConnector.humidityID,
							"Value": Hval}
				jsonHum = json.dumps(dictHum)
				r4 = requests.post(url+"add_sensor?Fridge_ID=" + deviceConnector.fridgeID, data=jsonHum)

				##### camera0
				C0senml = deviceConnector.get_camera0()
				C0val = ((C0senml['e'])[0])['v']
				dictC0 = {"sensor_ID": deviceConnector.camera0ID,
							"Value": C0val}
				jsonC0 = json.dumps(dictC0)
				r5 = requests.post(url+"add_sensor?Fridge_ID=" + deviceConnector.fridgeID, data=jsonC0)

				##### camera1
				C1senml = deviceConnector.get_camera1()
				C1val = ((C1senml['e'])[0])['v']
				dictC1 = {"sensor_ID": deviceConnector.camera1ID,
							"Value": C1val}
				jsonC1 = json.dumps(dictC1)
				r6 = requests.post(url+"add_sensor?Fridge_ID=" + deviceConnector.fridgeID, data=jsonC1)


				### register DeviceConnectorWS as a web service
				dictWS = {"name": ("DeviceConnectorWS_"+ deviceConnector.userID + "_" + deviceConnector.fridgeID),
									"IP": deviceConnector.ip,
									"port": deviceConnector.port}
				jsonWS = json.dumps(dictWS)
				r8 = requests.post(url+"add_WS", data=jsonWS)

				print("Fridge registered.")

				time.sleep(60)



if __name__ == '__main__':

	# get IP address of the RPI
	s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	devIP = s.getsockname()[0]
	devPort = 8082

	# read system configuration file
	try:
		configSystemFile = open("../configSystem.json", "r")
		configSystemJson = configSystemFile.read()
		configSystemDict = json.loads(configSystemJson)
		configSystemFile.close()
	except OSError:
		sys.exit("ERROR: cannot open the system configuration file.")

	# read DeviceConnector configuration file
	try:
		configDevConFile = open("configDeviceConnector.json", "r")
		configDevConJson = configDevConFile.read()
		configDevConDict = json.loads(configDevConJson)
		configDevConFile.close()
	except OSError:
		sys.exit("ERROR: cannot open the DeviceConnector configuration file.")

	
	catalogIP = configSystemDict["catalogIP"]
	catalogPort = configSystemDict["catalogPort"]

	userID = configDevConDict["userID"]
	fridgeID = configDevConDict["fridgeID"]
	temperatureID = configDevConDict["temperatureID"]
	humidityID = configDevConDict["humidityID"]
	camera0ID = configDevConDict["camera0ID"]
	camera1ID = configDevConDict["camera1ID"]

	print("Catalog IP is: " + catalogIP)
	print("Catalog port is " + catalogPort)

	# retrieve the broker IP and the broker port from the Catalog
	catalogURL = "http://" + catalogIP + ":" + catalogPort
	try:
		r = requests.get(catalogURL + "/broker")
		print(r)
		broker = r.json()
		brokerIP = broker["broker_IP"]
		brokerPort = broker["broker_port"]
	except requests.RequestException as err:
		sys.exit("ERROR: cannot retrieve the Broker IP from the Catalog.")


	# instantiate a DeviceConnector object
	deviceConnector = DeviceConnector(devIP, devPort, userID, fridgeID, temperatureID, humidityID, camera0ID, camera1ID)

	clientID = "DeviceConnectorWS_"+ deviceConnector.userID + "_" + deviceConnector.fridgeID

	deviceConnectorMQTT = DeviceConnectorMQTT(clientID, brokerIP, brokerPort, deviceConnector)
	deviceConnectorMQTT.start()

	tempThread = TemperatureThread(deviceConnector, deviceConnectorMQTT)
	humThread = HumidityThread(deviceConnector, deviceConnectorMQTT)
	cam0Thread = Camera0Thread(deviceConnector, deviceConnectorMQTT)
	cam1Thread = Camera1Thread(deviceConnector, deviceConnectorMQTT)
	regThread = RegistrationThread(deviceConnector, catalogIP, catalogPort)

	tempThread.start()
	humThread.start()
	cam0Thread.start()
	cam1Thread.start()
	regThread.start()

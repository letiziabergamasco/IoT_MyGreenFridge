# ----------------------------------------------------------------------
# Author: Letizia Bergamasco
# 
# Description: main functions used by the Products Control and the
# Consumption Control control strategies.
# ----------------------------------------------------------------------

import pybase64
from pyzbar.pyzbar import decode
import io
import numpy as np    
from PIL import Image
import cv2
import pybase64

import paho.mqtt.client as PahoMQTT
import threading
import time
import json
import requests
import sys


class ProductsController:

	def __init__(self):

		self.imageString = ""

	def getImage(self):

		return self.imageString

	def updateImage(self, imageString):

		self.imageString = imageString
		print("Image updated!")

	def imageToEan(self, imageString):

		# base64 decoding
		imageBytes = pybase64.b64decode(str(imageString))
	
		imagePIL = Image.open(io.BytesIO(imageBytes))

		imageArray = np.asarray(imagePIL)

		grayImage = cv2.cvtColor(imageArray, cv2.COLOR_BGR2GRAY)
		barcodes = decode(grayImage)
		
		if len(barcodes) == 1:
			EANBytes = barcodes[0].data
			EANcode = EANBytes.decode() # convert bytes into string
		else:
			EANcode = None

		print("EAN code is: " + str(EANcode))

		return EANcode


class ProductsControlMQTT:

	def __init__(self, clientID, broker, port, productsController, userID, fridgeID, sensorID, catalogIP, catalogPort, topicEnd):

		self.broker = broker
		self.port = port
		self.clientID = clientID


		#self.topic = topic
		self._isSubscriber = True

		# create an instance of paho.mqtt.client
		self._paho_mqtt = PahoMQTT.Client(clientID) 

		# register the callback
		self._paho_mqtt.on_connect = self.myOnConnect
		self._paho_mqtt.on_message = self.myOnMessageReceived

		self.productsController = productsController
		self.userID = userID
		self.fridgeID = fridgeID
		self.sensorID = sensorID
		self.catalogIP = catalogIP
		self.catalogPort = catalogPort
		self.topicEnd = topicEnd



	def myOnConnect (self, paho_mqtt, userdata, flags, rc):
		print ("Connected to broker: " + str(self.broker) + ", with result code: " + str(rc))

	def myOnMessageReceived (self, paho_mqtt , userdata, msg):
		# A new message is received
		#self.notifier.notify (msg.topic, msg.payload)
		#print("Message received: " + str(msg.payload))
		print("Message received: ...")
		print("On topic: ", str(msg.topic))

		message = json.loads(msg.payload.decode("utf-8"))

		imageString = ((message["e"])[0])["v"]

		# imageString is received on topicSubscribe and stored in productsController
		self.productsController.updateImage(imageString)

				
		### publish EANcode corresponding to imageString on the relative topic EAN0
		
		topicPublish = "MyGreenFridge/" + self.userID + "/" + self.fridgeID + "/" + self.topicEnd


		try:
			# get EANcode from imageString	
			EANcode = self.productsController.imageToEan(imageString)
				
		except: # catch all exceptions

			# if the EAN code cannot be retrieved, print an error
			e = sys.exc_info()[0]
			print("Invalid EAN code for user " + self.userID + " .")
			print(e)
			EANcode = None

		# EAN0: EANcode
		messageDict = {self.topicEnd: EANcode}
		messageJson = json.dumps(messageDict)
				
		# publish on topic EAN0 only if there is a valid EAN code
		if EANcode != None:
			# publish on topicPublish
			self.myPublish(topicPublish, messageJson)




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
		#self._topic = topic

	def start(self):
		# manage connection to broker
		self._paho_mqtt.connect(self.broker , self.port)
		self._paho_mqtt.loop_start()

	def stop (self):
		if (self._isSubscriber):
			# remember to unsuscribe if it is working also as subscriber
			self._paho_mqtt.unsubscribe(self._topic)

		self._paho_mqtt.loop_stop()
		self._paho_mqtt.disconnect()




class ProductsThread(threading.Thread):

		def __init__(self, productsControlMQTT, userID, fridgeID, sensorID, catalogIP, catalogPort, topicEnd):
			
			threading.Thread.__init__(self)
			self.productsControlMQTT = productsControlMQTT
			self.userID = userID
			self.fridgeID = fridgeID
			self.sensorID = sensorID
			self.catalogIP = catalogIP
			self.catalogPort = catalogPort
			self.topicEnd = topicEnd


		def run(self):

			url = "http://"+ self.catalogIP + ":"+ self.catalogPort + "/update_sensor?Fridge_ID=" + self.fridgeID

			while True:

				# subscribe to the topic related to camera0/camera1
				topicSubscribe = "MyGreenFridge/" + self.userID + "/" + self.fridgeID + "/" + self.sensorID
				self.productsControlMQTT.mySubscribe(topicSubscribe)
				
				# # imageString is received on topicSubscribe and stored in productsControlMQTT.productsController
				imageString = self.productsControlMQTT.productsController.getImage()

				# update sensor information on the Catalog
				dictC0 = {"sensor_ID": self.sensorID,
							"Value": imageString}
				jsonC0 = json.dumps(dictC0)
				r = requests.put(url, data=jsonC0)

				time.sleep(15)


class RegistrationThread(threading.Thread):
		
		def __init__(self, catalogIP, catalogPort, devIP, devPort, nameWS):
			
			threading.Thread.__init__(self)
			self.catalogIP = catalogIP
			self.catalogPort = catalogPort
			self.devIP = devIP
			self.devPort = devPort
			self.nameWS = nameWS
		
		def run(self):
			url = "http://"+ self.catalogIP + ":"+ self.catalogPort + "/add_WS"
			while True:

				### register ProductsControlWS as a web service
				dictWS = {"name": self.nameWS,
							"IP": self.devIP,
							"port": self.devPort}
				jsonWS = json.dumps(dictWS)
				r = requests.post(url, data=jsonWS)
				
				print(self.nameWS + " registered.")

				time.sleep(60)

def mainFunct(catalogIP, catalogPort, devIP, devPort, nameWS, sensorID, topicEnd):

	# retrieve the broker IP and the broker port from the Catalog
	catalogURL = "http://" + catalogIP + ":" + catalogPort
	try:
		r = requests.get(catalogURL + "/broker")
		broker = r.json()
		brokerIP = broker["broker_IP"]
		brokerPort = broker["broker_port"]
	except requests.RequestException as err:
		sys.exit("ERROR: cannot retrieve the Broker IP from the Catalog.")

	# register the web service on the Catalog
	regThread = RegistrationThread(catalogIP, catalogPort, devIP, devPort, nameWS)
	regThread.start()

	# initialize the list of fridges as an empty list
	initFridges = []

	controlThread = ControlThread(catalogIP, catalogPort, initFridges, nameWS, sensorID, topicEnd, brokerIP, brokerPort)
	controlThread.start()


class ControlThread(threading.Thread):
		
		def __init__(self, catalogIP, catalogPort, initFridges, nameWS, sensorID, topicEnd, brokerIP, brokerPort):
			
			threading.Thread.__init__(self)

			self.catalogIP = catalogIP
			self.catalogPort = catalogPort
			self.initFridges = initFridges
			self.nameWS = nameWS
			self.brokerIP = brokerIP
			self.brokerPort = brokerPort
			self.topicEnd = topicEnd
			self.sensorID = sensorID

		
		def run(self):

			
			catalogURL = "http://" + self.catalogIP + ":" + self.catalogPort
			oldFridges = self.initFridges

			while True:
			
				# retrieve all the fridges from the Catalog
				r = requests.get(catalogURL + "/fridges")
				dictCurrFridges = r.json() # fridges is a Python dictionary
				currFridges = []
				for fridge in dictCurrFridges["fridges"]:
					currFridges.append(fridge["ID"])


				# get new fridges that have been added
				diffFridges = list(set(currFridges) - set(oldFridges))
				
				# start what is needed for those fridges
				for fridgeID in diffFridges:

					for fridge in dictCurrFridges["fridges"]:
						
						if fridgeID == fridge["ID"]:

							userID =  fridge["user"]
							clientID = self.nameWS + "_" + userID + "_" + fridgeID

							productsController = ProductsController()
							productsControlMQTT = ProductsControlMQTT(clientID, self.brokerIP, self.brokerPort, productsController, userID, fridgeID, self.sensorID, self.catalogIP, self.catalogPort, self.topicEnd)
							productsControlMQTT.start()

							prodThread = ProductsThread(productsControlMQTT, userID, fridgeID, self.sensorID, self.catalogIP, self.catalogPort, self.topicEnd)
							prodThread.start()

				
				time.sleep(60*60)

				# update list of fridges
				oldFridges = currFridges.copy()


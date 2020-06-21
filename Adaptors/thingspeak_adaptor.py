import json
import paho.mqtt.client as PahoMQTT
import datetime
import time
import requests
import sys
import urllib.request
import cherrypy
import threading
import socket

class ThingSpeakDataManager:

	def __init__(self, client_ID, user_ID, fridge_ID, broker_ip, broker_port):
		self.user_ID = user_ID
		self.client_ID = client_ID
		self.fridge_ID = fridge_ID
		self.broker = broker_ip
		self.port = broker_port

		self._paho_mqtt = PahoMQTT.Client(self.client_ID)
		self._paho_mqtt.on_connect = self.myOnConnect
		self._paho_mqtt.on_message = self.myOnMessageReceived

		self.value_t = None
		self.value_h = None

	def myOnConnect(self, paho_mqtt, userdata, flags, rc):
		print("Connected to %s with result code: %d" %(self.broker, rc))

	def start(self):
		self._paho_mqtt.connect(self.broker, self.port)
		self._paho_mqtt.loop_start()

	def stop (self):

		if self._isSubscriber :
			self._paho_mqtt.unsubscribe(self.topic)

		self._paho_mqtt.loop_stop()
		self._paho_mqtt.disconnect()

	def mySubscribe(self, topic):
		#print("Subscribing to %s" %(topic))
		self._paho_mqtt.subscribe(topic, 2)

	def myOnMessageReceived (self, paho_mqtt, userdata, msg):

		message_received = json.loads(msg.payload.decode("utf-8"))
		message = int(((message_received["e"])[0])["v"])
		print("A message has been received.")
		if (msg.topic == "MyGreenFridge/"+str(self.user_ID)+"/"+str(self.fridge_ID)+"/temperature"):
			self.value_t = message
		elif(msg.topic == "MyGreenFridge/"+str(self.user_ID)+"/"+str(self.fridge_ID)+"/humidity"):
			self.value_h = message


class ThingSpeakThread(threading.Thread):
	
	def __init__(self, tsdm, userID, fridgeID, fridgeAPI, catalog_URL):
		threading.Thread.__init__(self)
		self.tsdm = tsdm
		self.userID = userID
		self.fridgeID = fridgeID
		self.fridgeAPI = fridgeAPI
		self.catalog_URL = catalog_URL

	def run(self):
		while True:

			### subscribe to temperature topic
			topic_t = "MyGreenFridge/"+str(self.userID)+"/"+str(self.fridgeID)+"/temperature"
			self.tsdm.mySubscribe(topic_t)

			### subscribe to humidity topic
			topic_h = "MyGreenFridge/"+str(self.userID)+"/"+str(self.fridgeID)+"/humidity"
			self.tsdm.mySubscribe(topic_h)

			### get number of wasted products
			try:
				r3 = requests.get(self.catalog_URL+"wasted?Fridge_ID="+self.fridgeID)
				wasted_json = r3.json()
				value_wasted = len(wasted_json["Wasted_products"])

				print ("Wasted products retrieved")
			
			except requests.RequestException as err:
				print("ERROR: did not find the list of wasted products")

			try:
			
				data_h = urllib.request.urlopen("https://api.thingspeak.com/update?api_key="+self.fridgeAPI+
					"&field1="+str(self.tsdm.value_t) +
					"&field2="+str(self.tsdm.value_h) +
					"&field3="+str(value_wasted))
				print("Values updated on ThingSpeak")

			except:
				print("ERROR: could not update the values on ThingSpeak")

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

				dictWS = {"name": self.nameWS,
							"IP": self.devIP,
							"port": self.devPort}
				jsonWS = json.dumps(dictWS)
				r = requests.post(url, data=jsonWS)
				
				print(self.nameWS + " registered.")

				time.sleep(60)

class ControlThread(threading.Thread):

		def __init__(self, catalogIP, catalogPort, initFridges, brokerIP, brokerPort):

			threading.Thread.__init__(self)

			self.catalogIP = catalogIP
			self.catalogPort = catalogPort
			self.initFridges = initFridges
			self.broker_IP = brokerIP
			self.broker_port = brokerPort


		def run(self):


			catalog_URL = "http://" + self.catalogIP + ":" + self.catalogPort + '/'
			oldFridges = self.initFridges

			while True:

				# retrieve all the fridges from the Catalog
				r = requests.get(catalog_URL + "fridges")
				i=0

				dictCurrFridges = r.json() # fridges is a Python dictionary
				currFridges = []
				for fridge in dictCurrFridges["fridges"]:
					currFridges.append(fridge["ID"])


				# get new fridges that have been added
				diffFridges = list(set(currFridges) - set(oldFridges))

				for fridge_ID in diffFridges:

					for f in dictCurrFridges["fridges"]:
						if fridge_ID == f["ID"]:
							userID = f["user"]
							fridgeID = f["ID"]
							fridgeAPI = f["API"]

							client_ID = "client_"+str(i)
							i = i+1


							tsdm = ThingSpeakDataManager(client_ID, userID, fridgeID, brokerIP, brokerPort)
							tsdm.start()

							tsThread = ThingSpeakThread(tsdm, userID, fridgeID, fridgeAPI, catalog_URL)
							tsThread.start()



				time.sleep(60*60)
				oldFridges = currFridges.copy()

if __name__ == "__main__":

	conf = {
		'/': {
			'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
			'tools.sessions.on': True
		}
	}

	try:
		configFile = open("../configSystem.json", "r")
		configJson = configFile.read()
		configDict = json.loads(configJson)
		configFile.close()
	except OSError:
		sys.exit("ERROR: cannot open the configuration file.")


	catalogIP = configDict['catalogIP']
	catalogPort = configDict['catalogPort']

	print("Catalog IP is: " + catalogIP)
	print("Catalog port is " + catalogPort)

	# get IP address
	s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	devIP = s.getsockname()[0]
	devPort = 8676
	
	nameWS = "ThingSpeakAdaptorWS"
	# register the web service on the Catalog
	regThread = RegistrationThread(catalogIP, catalogPort, devIP, devPort, nameWS)
	regThread.start()

	# retrieve the broker IP and the broker port from the Catalog
	catalogURL = "http://" + catalogIP + ":" + catalogPort
	try:
		r = requests.get(catalogURL + "/broker")
		broker = r.json()
		brokerIP = broker["broker_IP"]
		brokerPort = broker["broker_port"]
		print("Broker IP is: " + str(brokerIP))
		print("Broker port is: " + str(brokerPort))
	except requests.RequestException as err:
		sys.exit("ERROR: cannot retrieve the Broker IP from the Catalog.")

	initFridges = []

	controlThread = ControlThread(catalogIP, catalogPort, initFridges, brokerIP, brokerPort)
	controlThread.start()

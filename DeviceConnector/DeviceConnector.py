import Adafruit_DHT
import time
import select
import v4l2capture
from PIL import Image
import pybase64
import socket

class DeviceConnector(object):
    
    # constructor
    def __init__(self, ip, userID, fridgeID):

        # IP and port
        self.ip = ip
        self.port = "8080"
        
        # DHT22 sensor for temperature and humidity
        self.pin_dht = 17
        #initialize the DHT22 device
        self.dht_sensor = Adafruit_DHT.DHT22
        
        # camera0 path (picamera)
        self.camera0 = "/dev/video1"
        
        # camera1 path (usb camera)
        self.camera1 = "/dev/video1"
        
        # save userID and fridgeID
        self.userID = userID
        self.fridgeID = fridgeID


    def get_temperature(self):
    	"""retrieve temperature value from sensor DHT22 and return a senml with the temperature"""
        
    	# retrieve humidity and temperature from sensor DHT22
    	humidity, temperature = Adafruit_DHT.read_retry(self.dht_sensor, self.pin_dht)
    	
    	bn = "http://" + self.ip + "/Tsensor/" # base name
        n = "temperature" # resource name
        u = "Celsius" # units
        t = time.time() # timestamp

    	if temperature is not None:
                v = temperature # value	
    	else:
    		v = "Reading error"

    	Tsenml = {"bn": bn, "e": [{ "n": n, "u": u,"t": t, "v": v}]}
    	print ("Temperature is: " + str(v) + " Celsius")
    	
    	return Tsenml
    
    def get_humidity(self):
    	"""retrieve humidity value from sensor DHT22 and return a senml with the humidity"""
        
    	# retrieve humidity and temperature from sensor DHT22
    	humidity, temperature = Adafruit_DHT.read_retry(self.dht_sensor, self.pin_dht)
    	
    	bn = "http://" + self.ip + "/Hsensor/" # base name
        n = "humidity" # resource name
        u = "%" # units
        t = time.time() # timestamp

    	if humidity is not None:
                v = humidity # value	
    	else:
    		v = "Reading error"

    	Hsenml = {"bn": bn, "e": [{ "n": n, "u": u,"t": t, "v": v}]}
    	print ("Humidity is: " + str(v) + " %")
    	
    	return Hsenml
    
    def get_camera0(self):
        """retrieve an image from the camera0 and return it in a senml"""
        
        # open the video device
        video = v4l2capture.Video_device(self.camera0)
        # suggest image size to the device
        sizeX, sizeY = video.set_format(1280, 1024)
        # create a buffer to store image data
        video.create_buffers(1)
        # send the buffer to the device
        video.queue_all_buffers()
        # start the device
        video.start()
        # wait for the device to fill the buffer
        select.select((video,), (), ())
        # get image data
        image_data = video.read()
        # close the video device
        video.close()
        # save image in .jpg format
        image = Image.frombytes("RGB", (sizeX, sizeY), image_data)
        image.save("camera0image.jpg")
        
        with open("camera0image.jpg", "rb") as image_file:
            # base64 encoding
            image_base64 = pybase64.b64encode(image_file.read())
            
        bn = "http://" + self.ip + "/Camera0/" # base name
        n = "camera0" # resource name
        u = "base64" # units
        t = time.time() # timestamp
        
        if image_base64 is not None:
                v = image_base64 # value	
    	else:
    		v = "Reading error"

    	C0senml = {"bn": bn, "e": [{ "n": n, "u": u,"t": t, "v": v}]}
    	print ("Image captured from Camera0")
    	
    	return C0senml
        
    
    def get_camera1(self):
        """retrieve an image from the camera1 and return it in a senml"""
        
        # open the video device
        video = v4l2capture.Video_device(self.camera1)
        # suggest image size to the device
        sizeX, sizeY = video.set_format(1280, 1024)
        # create a buffer to store image data
        video.create_buffers(1)
        # send the buffer to the device
        video.queue_all_buffers()
        # start the device
        video.start()
        # wait for the device to fill the buffer
        select.select((video,), (), ())
        # get image data
        image_data = video.read()
        # close the video device
        video.close()
        # save image in .jpg format
        image = Image.frombytes("RGB", (sizeX, sizeY), image_data)
        image.save("camera1image.jpg")
        
        with open("camera1image.jpg", "rb") as image_file:
            # base64 encoding
            image_base64 = pybase64.b64encode(image_file.read())
            
        bn = "http://" + self.ip + "/Camera1/" # base name
        n = "camera1" # resource name
        u = "base64" # units
        t = time.time() # timestamp
        
        if image_base64 is not None:
                v = image_base64 # value	
    	else:
    		v = "Reading error"

    	C1senml = {"bn": bn, "e": [{ "n": n, "u": u,"t": t, "v": v}]}
    	print ("Image captured from Camera1")
    	
    	return C1senml
    
    
if __name__ == '__main__':
    
        # get IP address of the RPI
        s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0] # "192.168.1.128"
        
	dev = DeviceConnector(ip)
	dev.get_temperature()
	dev.get_humidity()
	dev.get_camera0()
	dev.get_camera1()
import time
from abc import ABCMeta
import logging

from .baseplatform import BasePlatform
import threading
import time
import math

import blinkt
import util
import random

blinkt.set_clear_on_exit()

logger = logging.getLogger(__name__)

blinkt.set_clear_on_exit()

start_time = time.time()

REDS = [0, 0, 0, 0, 0, 16, 64, 255, 64, 16, 0, 0, 0, 0, 0, 0]
BLUE = [0, 0, 0, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0, 0, 0, 0]

GPIO = None


class AlexaProcessIndicating(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		# Threading Event instance
		self.currEvent = threading.Event()

		'''
		self.lasttransit = util.millis()
		self.currStatus = True
		self.OFFINTERVAL = 300
		self.ONINTERVAL = 300
		'''
		self.start_time = time.time()

	def run(self):

		while not self.currEvent.isSet():
			### BLUE LARSON EFFECT
			delta = (time.time() - self.start_time) * 8
			offset = int(abs((delta % len(BLUE)) - blinkt.NUM_PIXELS))

			for i in range(blinkt.NUM_PIXELS):
				#blinkt.set_pixel(i, BLUE[offset + i], 0, 0)
				blinkt.set_pixel(i, 0, 0, BLUE[offset + i])
			blinkt.show()
			time.sleep(0.1)

		'''
		while not self.currEvent.isSet():
			if (self.currStatus):
				if (self.lasttransit + self.ONINTERVAL >= util.millis()):
					self.lasttransit = util.millis()
					self.currStatus = False
			else:
				if (self.lasttransit + self.OFFINTERVAL >= util.millis()):
					self.lasttransit = util.millis()
					self.currStatus = True

			for i in range(blinkt.NUM_PIXELS):
				if (self.currStatus == True):
					blinkt.set_pixel(i, 0x00, 0x00, 0xFF)
				else:
					blinkt.set_pixel(i, 0x00, 0x00, 0x00)
			blinkt.show()

			time.sleep(0.1)
		'''

class AlexaSpeakingIndicating(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		# Threading Event instance
		self.currEvent = threading.Event()

		self.last_time = util.millis()
		self.onStatus = True
		self.interval = self.getRandomInterval()
		self.displayOrange()

	def displayOrange(self):
		for i in range(blinkt.NUM_PIXELS):
			blinkt.set_pixel(i, 0x80, 0x23, 0x00)
		blinkt.show()

	def displayNone(self):
		for i in range(blinkt.NUM_PIXELS):
			blinkt.set_pixel(i, 0x00, 0x00, 0x00)
		blinkt.show()

	def getRandomInterval(self):
		return random.randrange(10, 500, 10)

	def run(self):
		while not self.currEvent.isSet():
			if((util.millis() - self.last_time) >= self.interval):
				self.last_time = util.millis()
				self.interval = self.getRandomInterval()

				if(self.onStatus == True):
					self.onStatus = False
					self.displayNone()
				else:
					self.onStatus = True
					self.displayOrange()
			time.sleep(0.01)


class RPiLikePlatform(BasePlatform):
	__metaclass__ = ABCMeta


	def __init__(self, config, platform_name, p_GPIO):
		global GPIO
		GPIO = p_GPIO
		super(RPiLikePlatform, self).__init__(config, platform_name)
		self.button_pressed = False
		self.processThreadProc = None
		self.speakThreadProc = None

	def setup(self):
		GPIO.setup(self._pconfig['button'], GPIO.IN, pull_up_down=GPIO.PUD_UP)

	def indicate_failure(self):
		for i in range(blinkt.NUM_PIXELS):
			blinkt.set_pixel(i, 0x80, 0x80, 0x80)
		blinkt.show()
		'''
		for _ in range(0, 5):
			time.sleep(.1)
			GPIO.output(self._pconfig['rec_light'], GPIO.HIGH)
			time.sleep(.1)
			GPIO.output(self._pconfig['rec_light'], GPIO.LOW)
		'''

	def indicate_success(self):
		for i in range(blinkt.NUM_PIXELS):
			blinkt.set_pixel(i, 0x80, 0x80, 0x80)
		blinkt.show()

	def after_setup(self, trigger_callback=None):
		self._trigger_callback = trigger_callback
		if self._trigger_callback:
			# threaded detection of button press
			GPIO.add_event_detect(self._pconfig['button'], GPIO.FALLING, callback=self.detect_button, bouncetime=100)

	def indicate_recording(self, state=True):
		if(state == True):
			for i in range(blinkt.NUM_PIXELS):
				blinkt.set_pixel(i, 0, 0x80, 0) # Green
		else:
			for i in range(blinkt.NUM_PIXELS):
				blinkt.set_pixel(i, 0, 0, 0)
		blinkt.show()

	def indicate_playback(self, state=True):
		if(state == True):
			if (self.speakThreadProc == None):
				self.speakThreadProc = AlexaSpeakingIndicating()
				self.speakThreadProc.start()
		else:
			if(self.speakThreadProc != None):
				if (self.speakThreadProc.isAlive()):
					self.speakThreadProc.currEvent.set()
					time.sleep(0.1)
					self.speakThreadProc = None

			for i in range(blinkt.NUM_PIXELS):
				blinkt.set_pixel(i, 0, 0, 0)
			blinkt.show()

	def indicate_processing(self, state=True):
		if(state == True):
			if (self.processThreadProc == None):
				self.processThreadProc = AlexaProcessIndicating()
				self.processThreadProc.start()
		else:
			if (self.processThreadProc.isAlive()):
				self.processThreadProc.currEvent.set()
				time.sleep(0.2)
				self.processThreadProc = None

			for i in range(blinkt.NUM_PIXELS):
				blinkt.set_pixel(i, 0, 0, 0)
			blinkt.show()

	def detect_button(self, channel=None): # pylint: disable=unused-argument
		self.button_pressed = True

		self._trigger_callback(self.force_recording)

		logger.debug("Button pressed!")

		time.sleep(.5)  # time for the button input to settle down
		while GPIO.input(self._pconfig['button']) == 0:
			time.sleep(.1)

		logger.debug("Button released.")

		self.button_pressed = False

		time.sleep(.5)  # more time for the button to settle down

	# def wait_for_trigger(self):
	# 	# we wait for the button to be pressed
	# 	GPIO.wait_for_edge(self._pconfig['button'], GPIO.FALLING)

	def force_recording(self):
		return self.button_pressed

	def cleanup(self):
		GPIO.remove_event_detect(self._pconfig['button'])
		for i in range(blinkt.NUM_PIXELS):
			blinkt.set_pixel(i, 0, 0, 0)

		#GPIO.output(self._pconfig['rec_light'], GPIO.LOW)
		#GPIO.output(self._pconfig['plb_light'], GPIO.LOW)

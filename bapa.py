import pyaudio
import wave
import sys

import RPi.GPIO as GPIO
import time
import apa102
import time
import threading
try:
    import queue as Queue
except ImportError:
    import Queue as Queue

class Pixels:
    PIXELS_N = 3

    def __init__(self):
        self.basis = [0] * 3 * self.PIXELS_N
        self.basis[0] = 2
        self.basis[3] = 1
        self.basis[4] = 1
        self.basis[7] = 2

        self.colors = [0] * 3 * self.PIXELS_N
        self.dev = apa102.APA102(num_led=self.PIXELS_N)

        self.next = threading.Event()
        self.queue = Queue.Queue()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def wakeup(self, direction=0):
        def f():
            self._wakeup(direction)

        self.next.set()
        self.queue.put(f)

    def listen(self):
        self.next.set()
        self.queue.put(self._listen)

    def think(self):
        self.next.set()
        self.queue.put(self._think)

    def speak(self):
        self.next.set()
        self.queue.put(self._speak)

    def off(self):
        self.next.set()
        self.queue.put(self._off)

    def _run(self):
        while True:
            func = self.queue.get()
            func()

    def _wakeup(self, direction=0):
        for i in range(1, 25):
            colors = [i * v for v in self.basis]
            self.write(colors)
            time.sleep(0.01)

        self.colors = colors

    def _listen(self):
        for i in range(1, 25):
            colors = [i * v for v in self.basis]
            self.write(colors)
            time.sleep(0.01)

        self.colors = colors

    def _think(self):
        colors = self.colors

        self.next.clear()
        while not self.next.is_set():
            colors = colors[3:] + colors[:3]
            self.write(colors)
            time.sleep(0.2)

        t = 0.1
        for i in range(0, 5):
            colors = colors[3:] + colors[:3]
            self.write([(v * (4 - i) / 4) for v in colors])
            time.sleep(t)
            t /= 2

        # time.sleep(0.5)

        self.colors = colors

    def _speak(self):
        colors = self.colors
        gradient = -1
        position = 24

        self.next.clear()
        while not self.next.is_set():
            position += gradient
            self.write([(v * position / 24) for v in colors])

            if position == 24 or position == 4:
                gradient = -gradient
                time.sleep(0.2)
            else:
                time.sleep(0.01)

        while position > 0:
            position -= 1
            self.write([(v * position / 24) for v in colors])
            time.sleep(0.01)

        # self._off()

    def _off(self):
        self.write([0] * 3 * self.PIXELS_N)

    def write(self, colors):
        for i in range(self.PIXELS_N):
            self.dev.set_pixel(i, int(colors[3*i]), int(colors[3*i + 1]), int(colors[3*i + 2]))

        self.dev.show()

BUTTON = 12

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# length of data to read.
chunk = 1024
RESPEAKER_INDEX = 1

# open the file for reading.
wf = wave.open('/home/pi/psm-phonebooth/bapa.wav', 'rb')

p = pyaudio.PyAudio()

# open stream based on the wave object which has been input.
stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                channels = wf.getnchannels(),
                rate = wf.getframerate(),
                output = True,
                output_device_index = RESPEAKER_INDEX)

pixels = Pixels()

pixels.wakeup()
time.sleep(3)
pixels.off()

while True:
    state = GPIO.input(BUTTON)
    if not state:
        print("off")
    else:
        print("on")
        pixels.wakeup()
        # create an audio object
        # open the file for reading.
        wf = wave.open('/home/pi/mic_hat/bapa.wav', 'rb')
        # read data (based on the chunk size)
        data = wf.readframes(chunk)
        # play stream (looping from beginning of file to the end)
        while data:
            state = GPIO.input(BUTTON)
            if not state:
                wf.close()
                break
            # writing to the stream is what *actually* plays the sound.
            stream.write(data)
            data = wf.readframes(chunk)
        pixels.off()
        wf.close()

    time.sleep(1)

# cleanup stuff.
stream.close()
p.terminate()
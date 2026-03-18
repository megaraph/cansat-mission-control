import serial

PORT = "/dev/cu.usbmodem5B5E1114511"

print("Data out:")
ser = serial.Serial(PORT, 9600)
while True:
    line = ser.readline().decode("utf-8").strip()
    print(line)

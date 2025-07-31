import serial
import threading

incomingBytes = []


def handle_serial_data(incomingBytes):
    print("Serial got:", incomingBytes)
    incomingBytes = []



try:
    # open the port: timeout=None means “block forever until size bytes arrive”
    ser = serial.Serial('COM5', timeout=None)
    print("Serial port opened.")
    while True:
        byte = ser.read(size=1)
        # print(f'IN -> : {byte}')
        if byte == b'\n':
            handle_serial_data(incomingBytes)
        else:
            incomingBytes.append(byte)

except Exception as e:
    print(f"Error: {e}")

finally:
    if ser.is_open:
        ser.close()
        print("Serial port closed.")
print("Exiting serial process.")

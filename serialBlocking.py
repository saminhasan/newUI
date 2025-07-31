import serial
import threading

incomingBytes = []


def handle_serial_data():
    global incomingBytes
    print("Serial got:", incomingBytes)
    incomingBytes = []


try:
    # open the port: timeout=None means “block forever until size bytes arrive”
    ser = serial.Serial("COM4", timeout=None)
    print("Serial port opened.")
    while True:
        print("LOOP")
        # byte = ser.read(size=8)
        bytes_in = ser.read_until(b"\n")
        print(f"IN -> : {bytes_in}")
        if bytes_in == b"\n":
            handle_serial_data()
        else:
            incomingBytes.append(bytes_in)

except Exception as e:
    print(f"Error: {e}")

finally:
    if ser.is_open:
        ser.close()
        print("Serial port closed.")
print("Exiting serial process.")

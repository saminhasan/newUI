from ssp import Teensy

FORMAT = "%(asctime)s:%(msecs)03d %(levelname)s %(name)s %(funcName)s %(message)s"
DATEFORMAT = "%Y-%m-%d %H-%M-%S"
import logging

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(FORMAT, DATEFORMAT))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

COM_PORT = "COM4"
if __name__ == "__main__":
    teensy = Teensy()
    teensy.connected

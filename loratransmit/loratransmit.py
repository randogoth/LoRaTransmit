#!/usr/bin/python3

import sys
import select
import argparse
from RNode import RNodeInterface

serialPort = "/dev/ttyACM0"

def rx(data, rnode):
	message = data.decode("utf-8")
	print("Received a packet: "+message)
	print("RSSI: "+str(rnode.r_stat_rssi)+" dBm")
	print("SNR:  "+str(rnode.r_stat_snr)+" dB")

def main():

	parser = argparse.ArgumentParser(description="LoRa packet transmitter for RNode hardware.")
	parser.add_argument("--freq", action="store", metavar="Hz", type=int, default=None, help="Frequency in Hz")
	parser.add_argument("--bw", action="store", metavar="Hz", type=int, default=125000, help="Bandwidth in Hz")
	parser.add_argument("--txp", action="store", metavar="dBm", type=int, default=2, help="TX power in dBm")
	parser.add_argument("--sf", action="store", metavar="factor", type=int, default=7, help="Spreading factor")
	parser.add_argument("--cr", action="store", metavar="rate", type=int, default=5, help="Coding rate")
	parser.add_argument("port", nargs="?", default=None, help="Serial port where RNode is attached", type=str)
	parser.add_argument("payload", nargs="?", default=None, help="The payload to be transmitted", type=str)
	args = parser.parse_args()

	if not (args.freq and args.bw and args.sf and args.cr):
		print("Please input startup configuration:")

	if not args.freq:
		print("Frequency in Hz:\t", end=' ')
		args.freq = int(input())
	
	if not args.payload and not select.select([sys.stdin, ], [], [], 0.0)[0]:
		print("Please provide a message to be sent")
		exit()

	try:
		rnode = RNodeInterface(
			callback = rx,
			name = "RandoRNode",
			port = args.port,
			frequency = args.freq,
			bandwidth = args.bw,
			txpower = args.txp,
			sf = args.sf,
			cr = args.cr,
			loglevel = RNodeInterface.LOG_NOTICE)
	except Exception as e:
		print(str(e))
		exit()

	if not args.payload and select.select([sys.stdin, ], [], [], 0.0)[0]:
		message = sys.stdin.read()
	else:
		message = ' '.join(args.payload)
	data = message.encode("utf-8")
	rnode.send(data)
	print(f"Payload sent: '{message}'\n")

if __name__ == "__main__":
	main()
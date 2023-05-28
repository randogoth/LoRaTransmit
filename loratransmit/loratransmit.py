#!/usr/bin/python3

import sys
import select
import argparse
from .RNode import RNodeInterface

def packetize(str):
    utf8_bytes = str.encode('utf-8')
    max_size = 255
    chunks = [utf8_bytes[i:i+max_size] for i in range(0, len(utf8_bytes), max_size)]
    return chunks

def main():

	parser = argparse.ArgumentParser(description="LoRa packet transmitter for RNode hardware.")
	parser.add_argument("--freq", action="store", metavar="Hz", type=int, default=None, help="Frequency in Hz")
	parser.add_argument("--bw", action="store", metavar="Hz", type=int, default=125000, help="Bandwidth in Hz")
	parser.add_argument("--txp", action="store", metavar="dBm", type=int, default=2, help="TX power in dBm")
	parser.add_argument("--sf", action="store", metavar="factor", type=int, default=7, help="Spreading factor")
	parser.add_argument("--cr", action="store", metavar="rate", type=int, default=5, help="Coding rate")
	parser.add_argument("port", nargs="?", default=None, help="Serial port where RNode is attached", type=str)
	parser.add_argument("payload", nargs="?", default=None, help="The payload to be transmitted", type=str)
	parser.print_usage = parser.print_help
	args = parser.parse_args()

	if not (args.freq and args.bw and args.sf and args.cr):
		print("Please input the LoRa frequency using the --freq argument")
	
	if not args.payload and not select.select([sys.stdin, ], [], [], 0.0)[0]:
		print("Please provide a message to be sent")
		exit()

	try:
		rnode = RNodeInterface(
			callback = None,
			name = "LoRaTransmitCLI",
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
		message = sys.stdin.read().rstrip()
	else:
		message = args.payload
	data = packetize(message)
	for chunk in data:
		rnode.queue(chunk)
	rnode.process_queue()
	rnode.log(f"Payload sent in {len(data)} packets!")

if __name__ == "__main__":
	main()
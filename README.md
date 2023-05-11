# LoRaTransmit

LoRa packet transmitter for RNode hardware 

## Usage

provide payload as command line argument or via pipe

```
usage: loratransmit [-h] [--freq Hz] [--bw Hz] [--txp dBm] [--sf factor]
                       [--cr rate]
                       [port] [payload]

LoRa packet transmitter for RNode hardware.

positional arguments:
  port         Serial port where RNode is attached
  payload      The payload to be transmitted

options:
  -h, --help   show this help message and exit
  --freq Hz    Frequency in Hz
  --bw Hz      Bandwidth in Hz
  --txp dBm    TX power in dBm
  --sf factor  Spreading factor
  --cr rate    Coding rate
```
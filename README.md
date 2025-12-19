Repository moved to [codeberg.org/randogoth/lora-transmit.git](https://codeberg.org/randogoth/lora-transmit.git)

# LoRaTransmit

Simple commandline raw LoRa packet transmitter for [RNode](https://unsigned.io/articles/2023_01_16_The_New_RNode_Ecosystem_Is_Here.html) hardware.

It's meant to be complementary to the packet sniffer [LoRaMon](https://github.com/markqvist/LoRaMon) and uses the latest [Python Module](https://github.com/markqvist/RNode_Firmware/tree/master/Python%20Module) that comes with the [RNode Firmware](https://github.com/markqvist/RNode_Firmware).

## Install

```
$ pip install loratransmit
```

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

## Example

Payload passed as argument

```
$ loratransmit --freq 917500000 /dev/ttyACM0 "Hello World"
```

Payload passed through pipe

```
$ echo "Hello World" | loratransmit --freq 917500000 /dev/ttyACM0
```
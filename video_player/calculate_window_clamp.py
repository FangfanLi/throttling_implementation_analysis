import sys
from pythonping import ping

# MSS in bytes
MSS = 1460
# Assuming traffic on port 80 has slightly higher RTT
RTT_INFLATION = 0.1

if len(sys.argv) != 2:
    print("please provide the throttling rate (Mbps) as a parameter")
    sys.exit(-1)

throttling_rate = float(sys.argv[1])

response_list = ping("3.82.13.40", size=40, count=10)

rtt_avg_ms = response_list.rtt_avg_ms
print("rtt_avg_ms", rtt_avg_ms)

cwnd = (throttling_rate * 10E6 / 8) * ((1 + RTT_INFLATION) * rtt_avg_ms / 10E3) / MSS

print("cwnd should be", cwnd)
import os
import subprocess
import sys


def clean_streaming_pcap(pcap_dir, client_ip, server_ip, server_port):

    for file in os.listdir(pcap_dir):
        if ".pcap" in file:
            filename = file.split(".")[0].split("_")
            isp = filename[0]
            side = filename[1]
            test_num = filename[2]
            if side == "client":
                filter = "port {} and host {}".format(server_port, server_ip)
            else:
                filter = "port {} and host {}".format(server_port, client_ip)
            command = ['tcpdump', '-r', "{}/{}".format(pcap_dir, file), '-w',
                       "{}/{}_{}_{}_out.pcap".format(pcap_dir, isp, side, test_num), filter]
            p = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main():
    if len(sys.argv) == 5:
        script, pcap_dir, client_ip, server_ip, server_port = sys.argv
    else:
        print("\r\n example run: python3 clean_streaming_pcaps.py pcap_dir client_ip server_ip server_port")
        sys.exit(1)

    clean_streaming_pcap(pcap_dir, client_ip, server_ip, server_port)


if __name__ == "__main__":
    main()
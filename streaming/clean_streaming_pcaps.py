import os
import subprocess
import sys


def clean_streaming_pcap(pcap_dir, client_ip, server_ip, server_port):

    for file in os.listdir(pcap_dir):
        if ".pcap" in file:
            filename = file.split(".pcap")[0]
            if "client" in filename:
                filter = "port {} and net {}/24".format(server_port, server_ip)
            else:
                filter = "port {} and net {}/24".format(server_port, client_ip)
            command = ['tcpdump', '-r', "{}/{}".format(pcap_dir, file), '-w',
                       "{}/{}_out.pcap".format(pcap_dir, filename), filter]
            p = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def clean_streaming_pcaps(pcap_dirs, client_ip, server_ip, server_port):
    for pcap_dir in os.listdir(pcap_dirs):
        if "DS" in pcap_dir:
            continue
        pcap_dir = "{}/{}".format(pcap_dirs, pcap_dir)
        for file in os.listdir(pcap_dir):
            if ".pcap" in file:
                filename = file.split(".pcap")[0]
                if "client" in filename:
                    filter = "port {} and net {}/24".format(server_port, server_ip)
                else:
                    filter = "port {} and net {}/24".format(server_port, client_ip)
                command = ['tcpdump', '-r', "{}/{}".format(pcap_dir, file), '-w',
                       "{}/{}_out.pcap".format(pcap_dir, filename), filter]
                p = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main():
    if len(sys.argv) == 5:
        script, pcap_dir, client_ip, server_ip, server_port = sys.argv
    else:
        print("\r\n example run: python3 clean_streaming_pcaps.py pcap_dir client_ip server_ip server_port")
        sys.exit(1)

    clean_streaming_pcaps(pcap_dir, client_ip, server_ip, server_port)


if __name__ == "__main__":
    main()
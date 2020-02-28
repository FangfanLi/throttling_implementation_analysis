import os
import subprocess
import sys
import plot_streaming_test_multiconn_seq


def plot_streaming_tests(stat_dir):

    for file in os.listdir(stat_dir):
        if ".json" in file:
            filename = file.split(".")[0]
            carrier = filename.split("_")[0]
            test_num = filename.split("_")[1]
            client_filename = "{}_client_{}".format(carrier, test_num)
            server_filename = "{}_server_{}".format(carrier, test_num)
            plot_streaming_test_multiconn_seq.do_all_plots("{}/{}_out.pcap".format(stat_dir, client_filename), "{}/{}_out.pcap".format(stat_dir, server_filename), client_filename, server_filename, "{}/{}".format(stat_dir, file))


def main():
    if len(sys.argv) == 2:
        script, stat_dir = sys.argv
    else:
        print("\r\n example run: python3 clean_streaming_pcaps.py stat_dir")
        sys.exit(1)

    plot_streaming_tests(stat_dir)


if __name__ == "__main__":
    main()
import os
import subprocess
import sys
import plot_streaming_test_multiconn_seq


def plot_streaming_tests(stat_dir):

    for file in os.listdir(stat_dir):
        if ".json" in file:
            # print(file)
            filename = file.split(".json")[0]
            client_filename = "{}_client".format(filename)
            server_filename = "{}_server".format(filename)
            plot_streaming_test_multiconn_seq.do_all_plots("{}/{}_out.pcap".format(stat_dir, client_filename), "{}/{}_out.pcap".format(stat_dir, server_filename), client_filename, server_filename, "{}/{}".format(stat_dir, file))


def main():
    if len(sys.argv) == 2:
        script, stat_dir = sys.argv
    else:
        print("\r\n example run: python3 plot_streaming_tests.py stat_dir")
        sys.exit(1)

    plot_streaming_tests(stat_dir)


if __name__ == "__main__":
    main()
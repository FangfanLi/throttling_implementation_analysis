#!/usr/bin/python3

import http.server
import socketserver
import socket
import sys
import subprocess
import os
PORT = 80

RESULTS_DIR = "/home/ec2-user/server_pcaps/"
TCPDUMP_PID = None
RESULT_DIR = ""
DUMP_NAME = ""


class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global TCPDUMP_PID
        global RESULTS_DIR
        global RESULT_DIR
        global DUMP_NAME
        if "network" in self.path:
            parameters = self.path.split("?")[1]
            # network = {} & cc = {} & headroom = {} & cwnd = {} & watermark = {} & i = {}
            parameters = parameters.split("&")
            network = parameters[0].split("=")[1]
            maxquality = parameters[1].split("=")[1]
            cc = parameters[2].split("=")[1]
            headroom = parameters[3].split("=")[1]
            cwnd = parameters[4].split("=")[1]
            watermark = parameters[5].split("=")[1]
            i = parameters[6].split("=")[1]
            dump_name = '{}_{}_{}_{}_{}_{}_{}_server.pcap'.format(network, maxquality, cc, headroom, cwnd, watermark, i)
            results_dir = "{}/{}/".format(RESULTS_DIR, network)
            if not os.path.exists(results_dir):
                os.mkdir(results_dir)
            results_dir = "{}/{}/".format(results_dir, cc)
            if not os.path.exists(results_dir):
                os.mkdir(results_dir)
            results_dir = "{}/{}_{}_{}_{}_{}".format(results_dir, maxquality, cc, headroom, cwnd, watermark)
            if not os.path.exists(results_dir):
                os.mkdir(results_dir)
            command = ['tcpdump', '-w', "{}/{}".format(results_dir, dump_name)]
            TCPDUMP_PID = subprocess.Popen(command)

        elif "endtest" in self.path:
            TCPDUMP_PID.terminate()
            TCPDUMP_PID = None

        """Serve a GET request."""
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def setup(self):
        self.timeout = 2
        http.server.BaseHTTPRequestHandler.setup(self)
        self.request.settimeout(2)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Connection", "keep-alive")
        http.server.SimpleHTTPRequestHandler.end_headers(self)


def main():
    tcp_window_clamp = -1
    if len(sys.argv) == 2:
        tcp_window_clamp = int(sys.argv[1])

    # Handler = http.server.SimpleHTTPRequestHandler
    Handler = MyRequestHandler
    Handler.protocol_version = "HTTP/1.1"
    Handler.extensions_map.update({
        '.m4s': 'video/MP2T',
    })

    httpd = socketserver.TCPServer(("", PORT), Handler, bind_and_activate=False)
 
    httpd.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_WINDOW_CLAMP, tcp_window_clamp)
    print("SND_CWND_CLAMP", httpd.socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_WINDOW_CLAMP))

    try:
        httpd.server_bind()
        httpd.server_activate()
    except:
        httpd.server_close()

    print("Serving at port", PORT)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

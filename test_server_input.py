#!/usr/bin/env python

'''
    Adapted from: https://wiki.python.org/moin/TcpCommunication
'''
import sys, os
import socket

TCP_IP = '127.0.0.1'
TCP_PORT = 8081
BUFFER_SIZE = 10240
 
file = sys.argv[1]
file = os.path.abspath(file)
file_name = os.path.basename(file)
content_length = os.stat(file).st_size
 
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)
 
conn, addr = s.accept()
print 'Connection from:', addr
while True:
    data = conn.recv(BUFFER_SIZE)
    if not data: break
    print data
    lines = data.split('\r\n')
    if lines[-1] == '':
        break
    
conn.send('HTTP/1.1 200 OK\r\n')
conn.send('Date: Wed, 24 Sep 2014 01:55:00 GMT\r\n')
conn.send('Content-Type: application/octet-stream\r\n')
conn.send('Content-Disposition: inline; filename="{0}"'.format(file_name))
conn.send("Content-Length: {0}\r\n".format(content_length))
conn.send('\r\n')
fd = open(file, 'rb')
while True:
    chunk = fd.read(BUFFER_SIZE)
    if not chunk:
        break
    conn.send(chunk)
conn.shutdown(socket.SHUT_RDWR)
conn.close()
fd.close()
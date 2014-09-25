#!/usr/bin/env python

'''
    Adapted from: https://wiki.python.org/moin/TcpCommunication
'''

import socket
 

TCP_IP = '127.0.0.1'
TCP_PORT = 8080
BUFFER_SIZE = 1024
 
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
conn.send('Date: Wed, 3 Sep 2014 01:55:00 GMT\r\n')
conn.send('Content-Type: text/plain\r\n')
conn.send('Content-Length: 0\r\n')
conn.send('Connection: close\r\n')
conn.send('\r\n')
conn.send('\r\n')
conn.shutdown(socket.SHUT_RDWR)
conn.close()
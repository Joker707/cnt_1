import socket
import threading
import time
import datetime

CLOSE_MESSAGE = ":q"

# connection
host = '127.0.0.1'
port = 9090
address = (host, port)

# start
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((host, port))
server.listen(10)

clients = {}

print("Server started!")


# send to all clients
def broadcast(sock, nick, t, msg_header, msg, file_header, file):
    for tmp in clients:
        if len(file) == 0 or sock != tmp:
            tmp.send(t + nick['header'] + nick['data'] + msg_header + msg + file_header + file)


# receive messages from clients
def read_part(client):
    while True:
        try:
            header = client.recv(5)
        except Exception as e:
            print("Connection reset: {}".format(str(e)))
            return dict()
        length = int.from_bytes(header, byteorder='big')
        try:
            msg = client.recv(length)
        except Exception as e:
            print("Connection reset: {}".format(str(e)))
            return dict()
        return {'header': header, 'data': msg}


def handle(client, address):
    if client not in clients:
        nickname = read_part(client)
        enc_time = int(datetime.datetime.utcnow().timestamp()).to_bytes(4, byteorder='big')
        if nickname in clients.values():
            error_message = 'nickname_error'
            header = len(error_message).to_bytes(5, byteorder='big')
            client.send(enc_time + nickname['header'] + nickname['data'] + header + error_message.encode('utf-8') + bytes([0]))
            return
        else:
            clients[client] = nickname
            print("[{}] Connected {}".format(time.strftime('%H:%M', time.localtime()), client.getpeername()))
            message = 'connected'
            header = len(message).to_bytes(5, byteorder='big')
            for tmp in clients:
                tmp.send(enc_time + nickname['header'] + nickname['data'] +
                         header + message.encode('utf-8') + bytes([0]))

    while True:
        enc_time = int(datetime.datetime.utcnow().timestamp()).to_bytes(4, byteorder='big')
        nickname = clients[client]
        message = read_part(client)
        file = read_part(client)
        if len(message['data']) == 0 or message['data'].decode('utf-8') == CLOSE_MESSAGE:
            left_message = 'disconnected'
            print('Connection from {} {} was closed'.format(nickname['data'].decode('utf-8'), client.getpeername()))
            del clients[client]
            left_message_len = len(left_message).to_bytes(5, byteorder='big')
            broadcast(client, nickname, enc_time, left_message_len, left_message.encode('utf-8'), file['header'], file['data'])
            break
        elif len(file['data']) > 0:
            print('Got file from {} with name {} and size {}'.format(nickname['data'].decode('utf-8'),
                                                                     message['data'].decode('utf-8'),
                                                                     int.from_bytes(file['header'], byteorder='big')))
            broadcast(client, nickname, enc_time, message['header'], message['data'], file['header'], file['data'])
        else:
            print('[{}] {}: {}'.format(
                datetime.datetime.utcnow().strftime('%H:%M'),
                nickname['data'].decode('utf-8'),
                message['data'].decode('utf-8')))
            broadcast(client, nickname, enc_time, message['header'], message['data'], file['header'], file['data'])


while True:
    # thread for clients
    client_socket, address_socket = server.accept()
    thread = threading.Thread(target=handle, args=(client_socket, address_socket)).start()

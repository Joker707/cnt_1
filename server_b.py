import datetime
import socket
import select
import time

CLOSE_MESSAGE = ":q"

host = '127.0.0.1'
port = 9091
address = (host, port)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(address)
server.listen()

sockets_list = [server]
clients = {}

print("Server started!")


def broadcast(sock, nick, t, msg_header, msg, file_header, file):
    for tmp in clients:
        if len(file) == 0 or sock != tmp:
            tmp.send(t + nick['header'] + nick['data'] + msg_header + msg + file_header + file)


def read_part(client):
    while True:
        try:
            header = client.recv(5)
        except Exception as e:
            print("Connection reset: {}".format(str(e)))
            return dict()
        length = int.from_bytes(header, byteorder='big', signed=False)
        try:
            msg = client.recv(length)
        except Exception as e:
            print("Connection reset: {}".format(str(e)))
            return dict()
        return {'header': header, 'data': msg}


while True:
    read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

    for socket in read_sockets:
        if socket == server:
            client, client_address = server.accept()
            nickname = read_part(client)
            enc_time = int(datetime.datetime.utcnow().timestamp()).to_bytes(4, byteorder='big')
            if nickname in clients.values():
                error_message = 'nickname_error'
                header = len(error_message).to_bytes(5, byteorder='big')
                client.send(enc_time + nickname['header'] + nickname['data'] +
                            header + error_message.encode('utf-8') + bytes([0]))
            else:
                clients[client] = nickname
                sockets_list.append(client)
                print("{} | Connected {}".format(time.strftime('%H:%M', time.localtime()), client.getpeername()))
                message = 'connected'
                header = len(message).to_bytes(5, byteorder='big')
                for tmp in clients:
                    if client != tmp:
                        tmp.send(enc_time + nickname['header'] + nickname['data'] +
                                 header + message.encode('utf-8') + bytes([0]))
        else:
            enc_time = int(datetime.datetime.utcnow().timestamp()).to_bytes(4, byteorder='big')
            nickname = clients[socket]
            message = read_part(socket)
            file = read_part(socket)
            if len(message['data']) == 0 or message['data'].decode('utf-8') == CLOSE_MESSAGE:
                left_message = 'disconnected'
                print('Connection from {} {} was closed'.format(nickname['data'].decode('utf-8'), socket.getpeername()))
                del clients[socket]
                sockets_list.remove(socket)
                left_message_len = len(left_message).to_bytes(5, byteorder='big')
                broadcast(socket, nickname, enc_time, left_message_len, left_message.encode('utf-8'),
                          file['header'], file['data'])
            elif len(file['data']) > 0:
                print('Got file from {} with name {} and size {}'
                      .format(nickname['data'].decode('utf-8'),
                              message['data'].decode('utf-8'),
                              int.from_bytes(file['header'], byteorder='big', signed=False)))

                broadcast(socket, nickname, enc_time, message['header'], message['data'], file['header'], file['data'])
            else:
                print('[{}] {}: {}'.format(
                    datetime.datetime.utcnow().strftime('%H:%M'),
                    nickname['data'].decode('utf-8'),
                    message['data'].decode('utf-8')))
                broadcast(socket, nickname, enc_time, message['header'], message['data'], file['header'], file['data'])
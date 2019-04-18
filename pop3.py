import socket
import ssl
import json
import re
import base64


def send(sock: socket.socket, command):
    sock.sendall(f'{command}\n'.encode())
    sock.settimeout(0.5)
    res = ''
    try:
        mess = sock.recv(BUFFER_SIZE).decode()
        while mess:
            res += mess
            mess = sock.recv(BUFFER_SIZE).decode()
    finally:
        return res


def log_in(sock: socket.socket):
    print(send(sock, f"USER {USERNAME}"))
    print(send(sock, f"PASS {PASSWORD}"))


def parse_content(answ: str):
    res = []

    boundary_reg = r'Content-Type: multipart/mixed;.\s+boundary="(.*?)"'
    boundary = re.findall(boundary_reg, answ)[0]

    n = answ.split(f'--{boundary}')[1:-1]

    content_type_reg = r'Content-Type: (.*?)\n'
    content_reg = r'\r\n\r\n((?:.*\r\n)*)'
    filename_reg = r'filename="(.*?)"'
    from_reg = r'From: .*? <(.*?)>'
    date_reg = r'Date: (.*?)\r\n'
    subject_reg = r'Subject: (.*?)\r\n'

    print(re.search(date_reg, answ).group(1))

    date = re.search(date_reg, answ).group(1)
    from_who = re.search(from_reg, answ).group(1)
    subject = re.search(subject_reg, answ).group(1)
    for e in n:
        e = e[1:]
        match_content_type = re.search(content_type_reg, e)
        match_content = re.search(content_reg, e)
        match_filename = re.search(filename_reg, e)
        content_type = match_content_type.group(1).replace(';', '')[:-1]
        content = match_content.group(1)[:-2]

        if match_filename:
            res.append((content_type, content, match_filename.group(1)))
        res.append((content_type, content, None))

    return res, date, from_who, subject


HOST = 'pop.yandex.ru'
PORT = 995
BUFFER_SIZE = 1024
USERNAME = 'vaspahomovTest1@yandex.ru'
PASSWORD = ''

if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv23)
        sock.connect((HOST, PORT))

        print(sock.recv(BUFFER_SIZE).decode())

        print(send(sock, f"USER {USERNAME}"))
        print(send(sock, f"PASS {PASSWORD}"))

        print(send(sock, "STAT"))
        print(send(sock, "LIST"))
        answ = send(sock, "RETR 1")
        contents, date, from_who, subject = parse_content(answ)

        print(f'From: {from_who} \r\n'
              f'Date: {date} \r\n'
              f'Subject: {subject}')

        for content_type, content, filename in contents:
            if 'text' in content_type:
                print(f'Message text: {content}')
            if not filename:
                continue
            else:
                with open('content_types.json') as f:
                    exts = json.loads(f.read())
                ext = exts[content_type]
                with open(f'attachments/{filename}', 'wb') as f:
                    f.write(base64.b64decode(content))

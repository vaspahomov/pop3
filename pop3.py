import socket
import ssl
import json
import re
import base64

HOST = 'pop.yandex.ru'
PORT = 995
BUFFER_SIZE = 1024
USERNAME = 'vaspahomovTest1@yandex.ru'
PASSWORD = 'QwertY1234'
ATTACHMENTS_DIRECTORY = 'attachments'


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
    ans = send(sock, f"USER {USERNAME}")
    print(ans)
    ans = send(sock, f"PASS {PASSWORD}")
    print(ans)


def parse_content(answ: str):
    res = []
    boundary_reg = r'Content-Type:\s+multipart/mixed;\s+boundary="(.*?)";'
    boundary = re.search(boundary_reg, answ).group(1)
    n = answ.split(f'--{boundary}')[2:-2]

    content_type_reg = r'Content--?Type: (.*?);'
    content_reg = r'\r\n\r\n((?:.*\r?\n)*)'
    filename_reg = r'filename="(.*?)"'
    from_reg = r'From:\s+<?(.*?)>?\r?\n'
    date_reg = r'Date: (.*?)\r?\n'
    subject_reg = r'Subject: (.*?)\r?\n'
    subject_reg_encoded = r'Subject: ((=?(.*?)\r??=\r\n)+)'
    message_text_reg = rf'--{boundary}\r?\n\r?\n(.*?)\r?\n--{boundary}'

    date = re.search(date_reg, answ).group(1)
    from_who = re.search(from_reg, answ).group(1)
    subject_encoded = re.search(subject_reg_encoded, answ).group(1)
    if subject_encoded:
        subject = decode_subject(subject_encoded)
    else:
        subject = re.search(subject_reg, answ).group(1)
    message_text = re.search(message_text_reg, answ).group(1)
    for e in n:
        e = e[1:]
        match_content_type = re.search(content_type_reg, e)
        match_content = re.search(content_reg, e)
        match_filename = re.search(filename_reg, e)
        content_type = match_content_type.group(1)
        content = match_content.group(1)[:-2]

        if match_filename:
            res.append((content_type, content, match_filename.group(1)))
        res.append((content_type, content, None))

    return res, date, from_who, subject, message_text


def decode_subject(encoded_subj: str) -> str:
    res = ''
    print(encoded_subj)
    for line in encoded_subj.split('\r\n  '):
        res += line[12:-2]
    return base64.b64decode(res.encode()).decode('utf-8')


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv23)
        sock.connect((HOST, PORT))

        print(sock.recv(BUFFER_SIZE).decode())

        log_in(sock)

        # print(send(sock, "STAT"))
        # print(send(sock, "LIST"))
        answ = send(sock, "RETR 1")
        contents, date, from_who, subject, message_text = parse_content(answ)
        print(f'Message has been received\r\n\r\n'
              f'From: {from_who} \r\n'
              f'Date: {date} \r\n'
              f'Subject: {subject}\r\n'
              f'Message text: {message_text}'
              f'\r\n')

        for content_type, content, filename in contents:
            if not filename:
                continue
            else:
                print(f'Attachment {filename} has been saved in {ATTACHMENTS_DIRECTORY}')
                with open('content_types.json') as f:
                    exts = json.loads(f.read())
                ext = exts[content_type.split()[0]]
                with open(f'{ATTACHMENTS_DIRECTORY}/{filename}', 'wb') as f:
                    f.write(base64.b64decode(content))

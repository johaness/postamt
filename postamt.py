from smtplib import SMTP, SMTP_SSL

from mimetypes import guess_type

from email import encoders
from email.header import make_header
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate


def send_mails(messages, host='localhost', port=25, user=None, password=None,
               starttls=False, ssl=False, ssl_key=None, ssl_cert=None,
               timeout=None):
    """
    Send ``messages``.

    :param Message messages: Message instance or list of Messages.
    :param str host:         hostname or ip of the SMTP server to use to send
                             the messages. Defaults to 'localhost'
    :param int port:         port the smtp server listens on. Defaults to 25.
                             Secure SMTP uses port 465, see ``ssl`` below.
    :param str user:         Username to authenticate with.
    :param str password:     Password for authentication.
    :param bool starttls:    If True, use STARTTLS. This is an SMTP extension
                             to initiate a secure connection with a SMTP server
                             listening on port 25.
    :param bool ssl:         Initialize a SSL protected connection to the
                             server. SSL protected SMTP typically runs on port
                             465. (Note that this is different then using the
                             ``starttls`` option).
    :param ssl_key str:      SSL private key file, PEM format
    :param ssl_cert str:     SSL certificate chain file, PEM format
    :param timeout int:      timeout in seconds
    """
    if ssl:
        server = SMTP_SSL(host, port, timeout=timeout,
                          keyfile=ssl_key, certfile=ssl_cert)
    else:
        server = SMTP(host, port, timeout=timeout)

    if starttls:
        server.ehlo()
        server.starttls()
        server.ehlo()

    if user and password:
        server.login(user, password)

    if isinstance(messages, Message):
        server.sendmail(*messages.compile())
    else:
        for m in messages:
            server.sendmail(*m.compile())

    server.quit()


class ListProperty(object):

    """Helper for setting recipients and cc from string or list"""

    def __init__(self, name):
        self.name = "__" + name

    def __get__(self, obj, objtype):
        return getattr(obj, self.name)

    def __set__(self, obj, value):
        if value is None:
            setattr(obj, self.name, [])
        elif isinstance(value, basestring):
            setattr(obj, self.name, [value])
        else:
            setattr(obj, self.name, list(value))


class Message(object):
    """
    Representation of an email message.

    :param sender:          sender of the message, e.g.
                            'ann@example.com' or 'Bob <bob@example.com>'
    :param recipients:      recipients of the email. This can be a str (single
                            recipient) or a list.
    :param subject:         the email subject.
    :param body:            plain text message body. Though not required,
                            Postamt encourages you to always send a plain
                            text version of you email.
    :param html:            the alternate message body, in html format.
    :param cc:              recipient(s) of a carbon copy. Can be a str or a
                            list.
    :param bcc:             recipient(s) of a blind carbon copy. Can be a str
                            or a list.
    :param reply_to:        reply recipient(s). Can be a str, list or None.
    :param date:            date and time of the email. If not supplied, this
                            is set for you to the current time and date. If you
                            want to set this, supply a float or integer with
                            POSIX time.
    :param charset:         character set the email in encoded in.
    :param headers:         extra headers to set in the email.
    """
    def __init__(self, sender=None, recipients=None, subject=None, body=None,
                 html=None, cc=[], bcc=[], reply_to=None, date=None,
                 charset='utf-8', headers={}):
        self.sender = sender
        self.recipients = recipients
        self.subject = subject
        self.body = body
        self.html = html
        self.cc = cc
        self.bcc = bcc
        self.reply_to = reply_to
        self.date = date
        self.charset = charset
        self.headers = headers
        self._inline = {}
        self._attach = {}

    def __repr__(self):
        return "<Message from='%s' to=%s subject='%s' body_len=%d>" % \
            (self.sender, self.recipients, self.subject, len(self.body or ''),)

    recipients = ListProperty('recipients')

    cc = ListProperty('cc')

    bcc = ListProperty('bcc')

    reply_to = ListProperty('reply_to')

    def set_date(self, value):
        self._date = formatdate(value)
    date = property(lambda self: self._date, set_date)

    def inline(self, cid, data, mimetype=None):
        self._inline[cid] = (data, mimetype)

    def attach(self, filename, data, mimetype=None):
        self._attach[filename] = (data, mimetype)

    def compile(self):
        assert self.sender, 'Message requires sender'
        assert self.recipients, 'Message requires at least one recipient'
        assert self.subject is not None, 'Message requires subject'

        msg = MIMEText(self.body, 'plain', self.charset)
        msg.add_header('Content-Disposition', 'inline')

        if self.html:

            part2 = MIMEText(self.html, 'html', self.charset)
            part2.add_header('Content-Disposition', 'inline')

            wrp = MIMEMultipart('alternative')
            wrp.attach(msg)
            wrp.attach(part2)
            msg = wrp

        if self._inline:
            ent = MIMEMultipart('related')
            ent.attach(msg)
            msg = ent
            for cid, (data, mt) in self._inline.iteritems():
                m = Message.__attach(data.read(), cid, mimetype=mt)
                m.add_header('Content-ID', '<%s>' % cid)
                m.add_header('Content-Disposition', 'inline')
                msg.attach(m)

        if self._attach:
            ent = MIMEMultipart('mixed')
            ent.attach(msg)
            msg = ent
            for fn, (data, mt) in self._attach.iteritems():
                m = Message.__attach(data.read(), fn, mimetype=mt)
                m.add_header('Content-Disposition', 'attachment', filename=fn)
                msg.attach(m)

        def encode_address(x):
            """Encode the name part of an Email address: Name <address>"""
            a = x.find(' <')
            if a == -1:
                return x
            return str(make_header([(x[:a], self.charset)])) + x[a:]

        encode_addresses = lambda x: ", ".join(encode_address(y) for y in x)

        msg['From'] = encode_address(self.sender)
        msg['To'] = encode_addresses(self.recipients)
        msg['Subject'] = str(make_header([(self.subject, self.charset)]))

        if self.cc:
            msg['CC'] = encode_addresses(self.cc)

        if self.reply_to:
            msg['Reply-To'] = encode_addresses(self.reply_to)

        msg['Date'] = self.date

        for hdr, val in self.headers.iteritems():
            msg[hdr] = val

        return (self.sender,
                self.recipients + self.cc + self.bcc,
                msg.as_string())

    @staticmethod
    def __attach(data, filename=None, mimetype=None):
        """Helper for creating attachments."""
        if mimetype:
            ctype = mimetype
            encoding = None
        else:
            ctype, encoding = guess_type(filename)
        if ctype is None or encoding is not None:
            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':
            # Note: we should handle calculating the charset
            msg = MIMEText(data, _subtype=subtype)
        elif maintype == 'image':
            msg = MIMEImage(data, _subtype=subtype)
        elif maintype == 'audio':
            msg = MIMEAudio(data, _subtype=subtype)
        else:
            msg = MIMEBase(maintype, subtype)
            msg.set_payload(data)
            # Encode the payload using Base64
            encoders.encode_base64(msg)

        return msg


def test():
    """Send out 6 test emails"""
    import os
    import sys

    assert len(sys.argv) == 4, 'Usage: postamt.py <from> <to> <smtp-server>'
    fro, to, srv = sys.argv[1:4]

    # generate test.png with ImageMagick
    os.system("convert -size 100x50 gradient:blue-grey -pointsize 40 " +
              "-tile gradient:red-orange -annotate +15+40 'test' test.png")

    s = []
    m = Message(fro, to, '1 - Plain Text', 'Plain text mail body')
    s.append(m)

    m = Message(fro, to, '2 - HTML', 'Plain text of HTML mail',
                '<h1>HTML</h1>text<i>styled</i>')
    s.append(m)

    m = Message(fro, to, '3 - Inline Image',
                '', 'Image <img src="cid:foo.png"> inline')
    m.inline("foo.png", file("test.png"))
    s.append(m)

    m = Message(fro, to, '4 - Attachment')
    m.attach("attached.png", file("test.png"))
    s.append(m)

    m = Message(fro, to, '5 - Inline Image & Attachment',
                'plain body', 'Image <img src="cid:foo.png"> inline')
    m.inline("foo.png", file("test.png"))
    m.attach("attached.png", file("test.png"))
    s.append(m)

    m = Message(fro, to,
                u'6 - Unicode \xdc\xf1\xef\xe7\xf8\u03b4\xe8'.encode('utf-8'),
                u'O, A and U umlauts: \xd6\xc4\xdc'.encode('utf-8'),
                u'Bold O, A and U umlaut: <b>\xd6\xc4\xdc</b>'.encode('utf-8'))
    s.append(m)

    send_mails(s, srv)


if __name__ == "__main__":
    test()

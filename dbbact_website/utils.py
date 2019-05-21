import sys
import smtplib
import os
import inspect
import datetime

debuglevel = 6


def debug(level, msg):
    """
    print a debug message

    input:
    level : int
        error level (0=debug, 4=info, 7=warning,...10=critical)
    msg : str
        the debug message
    """
    global debuglevel

    if level >= debuglevel:
        try:
            cf = inspect.stack()[1]
            cfile = cf.filename.split('/')[-1]
            cline = cf.lineno
            cfunction = cf.function
        except:
            cfile = 'NA'
            cline = 'NA'
            cfunction = 'NA'
        print('[%s] [%d] [%s:%s:%s] %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level, cfile, cfunction, cline, msg), file=sys.stderr, flush=True)


def SetDebugLevel(level):
    global debuglevel

    debuglevel = level


def getdoc(func):
    """
    return the json version of the doc for the function func
    input:
    func : function
            the function who's doc we want to return
    output:
    doc : str (html)
            the html of the doc of the function
    """
    print(func.__doc__)
    s = func.__doc__
    s = "<pre>\n%s\n</pre>" % s
    return(s)


def tolist(data):
    """
    if data is a string, convert to [data]
    if already a list, return the list
    input:
    data : str or list of str
    output:
    data : list of str
    """
    if isinstance(data, basestring):
        return [data]
    return data


def send_email(user, pwd, recipient, subject, body):
    gmail_user = user
    gmail_pwd = pwd
    FROM = user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        return ('successfully sent the mail')
    except:
        return ('failed to send mail')


def get_fasta_seqs(file):
    '''Get sequences from a fasta file

    Parameters
    ----------
    file : text file
        the text fasta file to process

    Returns
    -------
    seqs : list of str sequences (ACGT)
        the sequences in the fasta file
    '''
    debug(1, 'reading fasta file')
    seqs = []
    cseq = ''
    isfasta = False
    for cline in file:
        cline = cline.strip()
        if cline[0] == '>':
            isfasta = True
            if cseq:
                seqs.append(cseq)
            cseq = ''
        else:
            cseq += cline
    # process the last sequence
    if cseq:
        seqs.append(cseq)

    # test if we encountered '>'
    if not isfasta:
        debug(2, 'not a fasta file')
        return None

    debug(1, 'read %d sequences' % len(seqs))
    return seqs


def get_dbbact_server_address():
    '''
    Get the rest-api server address based on the environment variable DBBACT_WEBSITE_TYPE
    (use export DBBACT_WEBSITE_TYPE="main" / "develop" / "test")

    Parameters
    ----------

    Returns
    -------
    server_address : str
        the supercooldb server web address based on the env. variable
    '''
    # default values
    caddress = 'api.dbbact.org'
    cport = ''

    # first lets try defaults based on the server type
    if 'DBBACT_WEBSITE_TYPE' in os.environ:
        cenv = os.environ['DBBACT_WEBSITE_TYPE']
        debug(1, 'using server type %s from DBBACT_WEBSITE_TYPE' % cenv)
        if cenv == 'main':
            cport = 5001
        elif cenv == 'develop':
            cport = 7001
        elif cenv == 'test':
            cport = 5002
        else:
            debug(2, 'server type %s not recognized (should be main/develop/test. ignoring' % cenv)

    # now override with host/port
    if 'DBBACT_SERVER_HOST' in os.environ:
        caddress = os.environ['DBBACT_SERVER_HOST']
        debug(1, 'dbbact server address from DBBACT_SERVER_HOST set to %s' % caddress)
    if 'DBBACT_SERVER_PORT' in os.environ:
        cport = os.environ['DBBACT_SERVER_PORT']
        debug(1, 'dbbact server port from DBBACT_SERVER_PORT set to %s' % cport)

    server_address = 'http://%s:%s' % (caddress, cport)
    debug(2, 'using final dbbact api sever address %s' % server_address)
    return server_address


def get_dbbact_server_color(api_server_type=None):
    '''Return the color for the html header

    Parameters
    ----------
    api_server_type: str or None, optional
        if not None, compare to web server type and show red color if don't match

    Returns
    -------
    False if production (so keeps css color), '#00aa00' if development,  '#00aaaa' if other, '#aaaa00' if not set, '#aa0000' if mismatch with api_server
    '''
    if 'DBBACT_WEBSITE_TYPE' not in os.environ:
        return '#aaaa00'
    ctype = os.environ['DBBACT_WEBSITE_TYPE']
    if ctype == 'main':
        if api_server_type is not None:
            if api_server_type != 'dbbact':
                return '#aa0000'
        return False
    if ctype == 'develop':
        if api_server_type is not None:
            if api_server_type != 'dbbact_develop':
                return '#aa0000'
        return '#00aa00'
    debug(2, 'DBBACT_WEBSITE_TYPE is %s' % ctype)
    return '#00aaaa'

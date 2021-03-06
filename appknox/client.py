import logging
import sys
from urllib.parse import urlencode

import requests

from appknox.errors import MissingCredentialsError, InvalidCredentialsError, \
    ResponseError, InvalidReportTypeError
from appknox.constants import DEFAULT_VULNERABILITY_LANGUAGE, \
    DEFAULT_APPKNOX_URL, DEFAULT_REPORT_LANGUAGE, DEFAULT_OFFSET, \
    DEFAULT_LIMIT, DEFAULT_REPORT_FORMAT, DEFAULT_SECURE_CONNECTION

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("appknox")


class AppknoxClient(object):
    """
    Appknox Client
    """

    def login(self):
        """
        Login and Get token
        """
        login_url = "%s/token/new.json" % self.api_base
        data = {
            'username': self._username,
            'password': self._password,
        }
        logger.debug('Logging In: %s', login_url)
        try:
            response = requests.post(login_url, data=data)
        except requests.exceptions.ConnectionError:
            print('Unable to connect to server. Please try after sometime.')
            sys.exit(0)
        json = response.json()
        if not json['success']:
            raise InvalidCredentialsError
        self.token = json['token']
        self.user = str(json['user'])
        print(json)

    def __init__(
            self, username=None, password=None, api_key=None,
            host=DEFAULT_APPKNOX_URL, secure=DEFAULT_SECURE_CONNECTION,
            auto_login=True):
        if username and password:
            self.basic_auth = True
            self._username = username
            self._password = password
        # API auth comes later
        # elif api_key:
        #     self.basic_auth = False
        #     self.api_key = api_key
        else:
            raise MissingCredentialsError
        protocol = 'http'
        if secure:
            protocol += 's'
        self.api_base = "%s://%s/api" % (protocol, host)
        self.login()

    def _request(self, req, endpoint, data={}):
        """
        Make a request
        """
        url = "%s/%s" % (self.api_base, endpoint)
        logger.debug('Making a request: %s', url)
        response = req(url, data=data, auth=(self.user, self.token))
        if response.status_code > 299 or response.status_code < 200:
            # f = open("error.html", "w")
            # f.write(response.content.decode())
            # f.close()
            raise ResponseError(response.content)
        try:
            return response.json()
        except ValueError:
            return response.content.decode()

    def current_user(self):
        """
        docstring for current_user
        """
        url = 'users/' + str(self.user)
        return self._request(requests.get, url)

    def submit_url(self, store_url):
        """
        Submit a play store URL
        """
        data = {"storeURL": store_url}
        return self._request(requests.post, 'store_url', data)

    def upload_file(self, _file):
        """
        `_file` is a file-type object
        """
        data = {'content_type': 'application/octet-stream'}
        json = self._request(requests.get, 'signed_url', data)
        url = json['url']
        logger.info('Please wait while uploading file..: %s', url)
        response = requests.put(url, data=_file.read())
        # print(response.content, response.status_code)
        data = {
            "file_key": json['file_key'],
            "file_key_signed": json['file_key_signed'],
        }
        url = "%s/uploaded_file" % self.api_base
        response = requests.post(
            url, data=data, auth=(self.user, self.token))
        return response.json()

    def project_get(self, project_id):
        """
        get project details with project id
        """
        url = 'projects/' + str(project_id)
        return self._request(requests.get, url)

    def project_list(
            self, limit=DEFAULT_LIMIT, offset=DEFAULT_OFFSET):
        """
        return list of projects
        """
        params = {'limit': limit, 'offset': offset}
        url = 'projects?%s' % (urlencode(params))
        return self._request(requests.get, url)

    def file_get(self, file_id):
        """
        get file details with file id
        """
        url = 'files/' + str(file_id)
        return self._request(requests.get, url)

    def file_list(
            self, project_id, limit=DEFAULT_LIMIT, offset=DEFAULT_OFFSET):
        """
        return list of files for a project
        """
        params = {'projectId': project_id, 'offset': offset, 'limit': limit}
        url = 'files?%s' % (urlencode(params))
        return self._request(requests.get, url)

    def dynamic_start(self, file_id):
        url = 'dynamic/{}'.format(str(file_id))
        return self._request(requests.get, url)

    def dynamic_stop(self, file_id):
        url = 'dynamic_shutdown/{}'.format(str(file_id))
        return self._request(requests.get, url)

    def dynamic_restart(self, file_id):
        self.dynamic_stop(file_id)
        return self.dynamic_start(file_id)

    def analyses_list(self, file_id):
        """
        get analyses details with file id
        """
        url = 'files/' + str(file_id)
        return self._request(requests.get, url)

    def report(
            self, file_id, format_type=DEFAULT_REPORT_FORMAT,
            language=DEFAULT_REPORT_LANGUAGE):
        """
        get report in specified format
        """
        if format_type not in ['json', 'pdf']:
            raise InvalidReportTypeError("Invalid format type")
        if language not in ['en', 'ja']:
            raise InvalidReportTypeError("Unsupported language")

        params = {'format': format_type, 'language': language}
        url = 'report/%s?%s' % (str(file_id), urlencode(params))
        return self._request(requests.get, url)

    def payment(self, card):
        data = {'card', card}
        return self._request(requests.post, 'stripe_payment', data)

    def vulnerability(
            self, vulnerability_id, language=DEFAULT_VULNERABILITY_LANGUAGE):
        url = 'vulnerabilities/' + str(vulnerability_id)
        return self._request(requests.get, url)

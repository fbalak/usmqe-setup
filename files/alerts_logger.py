#!/usr/bin/env python
"""Tendrl Notifier REST API logger."""

import argparse
import ConfigParser
import logging
import os
import json
import time

import requests


URL = "http://0.0.0.0/api/1.0/"

class TendrlAuth(requests.auth.AuthBase):
    """
    Implementation of Tendrl Auth Method (Bearer Token) for requests
    library, based on upstream documentation:
    https://github.com/Tendrl/api/blob/master/docs/authentication.adoc
    This way, auth. implementation is stored in a single place and it also
    makes possible to omit auth object entrirely (thanks to design of
    requests library) for testing purposes (eg. checks of corner cases to make
    sure that security is not compromised) no matter if it makes sense from
    Tendrl user perspective.
    See also: http://docs.python-requests.org/en/master/user/authentication/
    """

    def __init__(self, token, username=None):
        """
        Args:
            token (str): tendrl ``access_token`` string
            username (str): username of account associated with the token
        """
        self.__bearer_token = token
        # metadata attributes for easier debugging, we need to trust login
        # function to store correct values there
        self.username = username

    def __repr__(self):
        return "TendrlAuth(token={})".format(self.__bearer_token)

    def __call__(self, r):
        """
        Add Tendl Bearer Token into header of the request.
        For full description, see requests documentation:
        http://docs.python-requests.org/en/master/user/authentication/
        """
        headers = {
            "Authorization": "Bearer {}".format(self.__bearer_token),
            }
        r.prepare_headers(headers)
        return r


def login(username, password, asserts_in=None):
    """
    Login Tendrl user.
    Args:
        username: name of user that is going logged in
        password: password for username
        asserts_in: assert values for this call and this method
    Returns requests auth object (instance of TendrlAuth)
    """
    pattern = "login"
    post_data = {"username": username, "password": password}
    request = requests.post(
        URL + pattern,
        data=json.dumps(post_data))
    token = request.json().get("access_token")
    auth = TendrlAuth(token, username)
    return auth


def logout(auth, asserts_in=None):
    """
    Logout Tendrl user.
    Args:
        asserts_in: assert values for this call and this method
        auth: TendrlAuth object (defines bearer token header)
    """
    pattern = "logout"
    request = requests.delete(
        URL + pattern,
        auth=auth)
    return request.json()


class TendrlApi(object):
    """ Common methods for Tendrl REST API.
    """

    def __init__(self, auth=None):
        """
        Args:
            auth: TendrlAuth object (defines bearer token header), when auth is
               None, requests are send without athentication header
        """
        # requests auth object with so called tendrl bearer token
        self._auth = auth

    def alerts(self):
        """ Alerts REST API
        Name:        "alerts",
        Method:      "GET",
        Pattern:     "alerts",
        """
        response = requests.get(
            URL + "alerts",
            auth=self._auth,)
        return response.json()


class TendrlFormatter(logging.Formatter):
    """
    This class can be used to create special formating of tendrl logs.
    """
    def format(self, record):
        # TODO(fbalak): update this function to alter log format
        result = super(TendrlFormatter, self).format(record)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("user", type=str, nargs='?')
    args = parser.parse_args()
    config = ConfigParser.RawConfigParser()
    thisfolder = os.path.dirname(os.path.abspath(__file__))
    config.read(os.path.join(thisfolder, "users.ini"))
    password = config.get(args.user, "password")
    auth = login(args.user, password)
    api = TendrlApi(auth=auth)
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    logger = logging.getLogger("tendrl-notifier.{}".format(args.user))
    formatter = TendrlFormatter(logging.BASIC_FORMAT)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    last_alerts = []
    while(True):
        alerts = api.alerts()
        for alert in alerts:
            if alert not in last_alerts:
                logger.info(alert)
        last_alerts = alerts
        time.sleep(10)


if __name__ == "__main__":
    main()
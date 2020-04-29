
# Copyright 2020 Chas Berndt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
# SOFTWARE

import json
import requests
import logging as log
from time import sleep
import argparse


logging_format = '%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s'
log.basicConfig(level=log.DEBUG, format=logging_format)


class DODatabaseCreationException(Exception):
    pass


class DODatabase(object):

    def __init__(self, action, do_api_token, dbs_name, dbs_region, db_user, database, whitelist_ip):
        self.action = action
        self.do_api_token = do_api_token
        self.dbs_name = dbs_name
        self.dbs_region = dbs_region
        self.db_user = db_user
        self.database = database
        self.whitelist_ip = whitelist_ip
        self.api_endpoint = 'https://api.digitalocean.com/v2'
        # TODO: Make the following values configurable.
        self.size = 'db-s-1vcpu-1gb'
        self.engine = 'mysql'
        self.version = '8'
        self.num_nodes = 1
        self.type = 'ip_addr'
        self.auth_plugin = 'mysql_native_password'
        self.wait = True

        self.state_changed = False

        if action.lower() == 'create':
            self.create()
        elif action.lower() == 'destroy':
            self.destroy()
        elif action.lower() == 'info':
            pass

    def api_call(self, url, method, token, data=None):
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        if method.upper() == 'POST':
            response = requests.post(url, headers=headers, data=data)
        if method.upper() == 'PUT':
            response = requests.put(url, headers=headers, data=data)
        if method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        return response.status_code or None, response.text or None

    def create_dbs_json(self):
        create_dbs = {'name': self.dbs_name, 'engine': self.engine, 'version': self.version, 'size': self.size,
                      'region': self.dbs_region, 'num_nodes': self.num_nodes}
        return json.dumps(create_dbs)

    def configure_dbs_json(self):
        configure_dbs = {'rules': [{'type': self.type, 'value': self.whitelist_ip}]}
        return json.dumps(configure_dbs)

    def create_db_json(self):
        create_db = {'name': self.database}
        return json.dumps(create_db)

    def create_db_user_json(self):
        create_db_user = {'name': self.db_user, 'mysql_settings': {'auth_plugin': self.auth_plugin}}
        return json.dumps(create_db_user)

    def create_database_server(self):
        status, content = self.api_call(f'{self.api_endpoint}/databases', 'POST', self.do_api_token,
                                        self.create_dbs_json())
        content = json.loads(content)
        if status == 422:
            log.warning(f'This database server likely exists. Status Code: {status} Response from API: {content}')
            return self.get_database_info()
        else:
            if self.wait:
                while self.get_dbs_state() == 'creating':
                    log.info('Waiting for database to be in online state.')
                    sleep(15)
            return content

    def get_database_info(self):
        status, content = self.api_call(f'{self.api_endpoint}/databases/', 'GET', self.do_api_token)
        content = json.loads(content)
        return content

    def get_database_id(self):
        content = self.get_database_info()
        for database_server in content['databases']:
            if database_server['name'] == self.dbs_name:
                return database_server['id']
        return None

    def get_dbs_state(self):
        content = self.get_database_info()
        for database_server in content['databases']:
            if database_server['name'] == self.dbs_name:
                return database_server['status']

    def create_database(self):
        status, content = self.api_call(f'{self.api_endpoint}/databases/{self.get_database_id()}/dbs', 'POST',
                                        self.do_api_token, self.create_db_json())
        content = json.loads(content)
        if status == 422:
            log.warning(f'This database likely exists. Status Code: {status} Response from API: {content}')
            return None
        else:
            self.state_changed = True
            return content

    def configure_database(self):
        status, content = self.api_call(f'{self.api_endpoint}/databases/{self.get_database_id()}/firewall', 'PUT',
                                        self.do_api_token, self.configure_dbs_json())
        if status == 422:
            log.warning(f'This IP address has already been whitelisted. Status Code: {status} Response from API: {content}')
            return None
        else:
            self.state_changed = True
            return None

    def create_db_user(self):
        status, content = self.api_call(f'{self.api_endpoint}/databases/{self.get_database_id()}/users', 'POST',
                                        self.do_api_token, self.create_db_user_json())
        content = json.loads(content)
        if status == 422:
            log.warning(f'This database user likely exists. Status Code: {status} Response from API: {content}')
            return None
        else:
            self.state_changed = True
            return content

    def destroy_database(self):
        status, content = self.api_call(f'{self.api_endpoint}/databases/{self.get_database_id()}', 'DELETE',
                                        self.do_api_token)
        if status in [404, 422, 500]:
            log.warning(f'This database server likely does not exist. Status Code: {status}')
            return None
        else:
            self.state_changed = True
            return True

    def create(self):
        log.info('Creating database server.')
        dbs_result = self.create_database_server()
        log.info(f'Create DBS API response: {dbs_result}')
        self.configure_database()
        db_result = self.create_database()
        log.info(f'Create db API response: {db_result}')
        usr_result = self.create_db_user()
        log.info(f'Create db user API response: {usr_result}')

    def destroy(self):
        log.info('Destroying database server.')
        destroy_result = self.destroy_database()
        if destroy_result is not None:
            log.info(f'Database server has been destroyed.')
        else:
            log.info(f'No database server destroyed. Likely, a database server named {self.dbs_name} did not exist.')
        return self.get_database_info()

    def info(self):
        log.info('Getting information about database server.')
        return self.get_database_info()

    def friendly_output(self):
        return json.dumps(self.get_database_info())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', '-a', required=True, help='Actions available: create, destroy.')
    parser.add_argument('--token', '-t', required=True, help='DigitalOcean API token.')
    parser.add_argument('--server_name', '-s', required=True, help='Desired database server name.')
    parser.add_argument('--region', '-r', required=True, help='Desired region for database server. Ex: nyc1')
    parser.add_argument('--database_user', '-u', required=True, help='Desired database user name.')
    parser.add_argument('--database_name', '-d', required=True, help='Desired database name.')
    parser.add_argument('--allowed-ip', '-i', required=True, help='IP address allowed to connect to database server.')
    parser.add_argument('--output', '-o', required=False, help='Path where database information should be written to. '
                                                               'If not provided, information is printed to stdout.')
    args = parser.parse_args()

    database = DODatabase(args.action, args.token, args.server_name, args.region, args.database_user,
                          args.database_name, args.allowed_ip)

    if args.output is None:
        print(database.friendly_output())
    else:
        with open(args.output, 'w') as out_file:
            out_file.write(database.friendly_output())


if __name__ == '__main__':
    main()

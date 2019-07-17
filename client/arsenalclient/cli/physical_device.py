'''Arsenal client physical_device command line helpers.

These functions are called directly by args.func() to invoke the
appropriate action. They also handle output formatting to the commmand
line.

'''
#
#  Copyright 2015 CityGrid Media, LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from __future__ import print_function
import logging
import sys
import csv
import json
from arsenalclient.cli.common import (
    _check_tags,
    ask_yes_no,
    check_resp,
    parse_cli_args,
    print_results,
    update_object_fields,
    )
from arsenalclient.exceptions import NoResultFound

LOG = logging.getLogger(__name__)
UPDATE_FIELDS = [
    'oob_ip_address',
    'oob_mac_address',
]
TAG_FIELDS = [
    'set_tags',
    'del_tags',
]

def _format_msg(results, tags=None):
    '''Format the message to be passed to ask_yes_no().'''

    r_names = []
    for res in results:
        resp = _check_tags(res, tags)
        if resp:
            r_names.append('{0}\n{1}'.format(res['serial_number'],
                                             resp))
        else:
            r_names.append('{0}'.format(res['serial_number']))

    msg = 'We are ready to update the following physical_devices: ' \
          '\n {0}\nContinue?'.format('\n '.join(r_names))

    return msg

def process_actions(args, client, results):
    '''Process change actions for physical_locations search results.'''

    resp = None
    if args.set_tags:
        msg = _format_msg(results, args.set_tags)
        if ask_yes_no(msg, args.answer_yes):
            tags = [tag for tag in args.set_tags.split(',')]
            for tag in tags:
                name, value = tag.split('=')
                resp = client.tags.assign(name, value, 'physical_locations', results)

    if args.del_tags:
        msg = _format_msg(results, args.del_tags)
        if ask_yes_no(msg, args.answer_yes):
            tags = [tag for tag in args.del_tags.split(',')]
            for tag in tags:
                name, value = tag.split('=')
                resp = client.tags.deassign(name, value, 'physical_locations', results)

    if any(getattr(args, key) for key in UPDATE_FIELDS):
        msg = _format_msg(results)
        if ask_yes_no(msg, args.answer_yes):
            for physical_device in results:
                pd_update = update_object_fields(args,
                                                 'physical_device',
                                                 physical_device,
                                                 UPDATE_FIELDS)

                client.physical_devices.update(pd_update)

    return resp

def search_physical_devices(args, client):
    '''Search for physical_devices and perform optional assignment
       actions.'''

    LOG.debug('action_command is: {0}'.format(args.action_command))
    LOG.debug('object_type is: {0}'.format(args.object_type))

    resp = None

    action_fields = UPDATE_FIELDS + TAG_FIELDS
    search_fields = args.fields

    # If we are adding or deleting tags, we need existing tags for comparison.
    if args.set_tags or args.del_tags:
        if args.fields:
            args.fields += ',tags'
        else:
            args.fields = 'tags'

    if any(getattr(args, key) for key in UPDATE_FIELDS):
        search_fields = 'all'

    params = parse_cli_args(args.search, search_fields, args.exact_get, args.exclude)
    resp = client.physical_devices.search(params)

    if not resp.get('results'):
        return resp

    results = resp['results']

    # Allows for multiple actions to be performed at once.
    if not any(getattr(args, key) for key in action_fields):

        if args.audit_history:
            results = client.physical_locations.get_audit_history(results)

        print_results(args, results, default_key='serial_number', skip_keys=['serial_number', 'id'])

    else:

        resp = process_actions(args, client, results)

    if resp:
        check_resp(resp)
    LOG.debug('Complete.')

def create_physical_device(args, client, device=None):
    '''Create a new physical_device.'''

    try:
        serial_number = device['serial_number']
    except TypeError:
        serial_number = args.serial_number

        device = {
            'hardware_profile': args.hardware_profile,
            'mac_address_1': args.mac_address_1,
            'mac_address_2': args.mac_address_2,
            'oob_ip_address': args.oob_ip_address,
            'oob_mac_address': args.oob_mac_address,
            'physical_elevation': args.physical_elevation,
            'physical_location': args.physical_location,
            'physical_rack': args.physical_rack,
            'serial_number': args.serial_number,
        }

    LOG.info('Checking if physical_device serial_number exists: {0}'.format(serial_number))

    try:

        resp = client.physical_devices.get_by_serial_number(serial_number)

        if ask_yes_no('Entry already exists for physical_device name: {0}\n Would you ' \
                      'like to update it?'.format(resp['serial_number']),
                      args.answer_yes):

            resp = client.physical_devices.update(device)
            return check_resp(resp)

    except NoResultFound:
        resp = client.physical_devices.create(device)
        return check_resp(resp)

def delete_physical_device(args, client):
    '''Delete an existing physical_device.'''

    LOG.debug('action_command is: {0}'.format(args.action_command))
    LOG.debug('object_type is: {0}'.format(args.object_type))

    try:
        results = client.physical_devices.get_by_serial_number(args.physical_device_serial_number)

        msg = 'We are ready to delete the following {0}: ' \
              '\n{1}\n Continue?'.format(args.object_type, results['serial_number'])

        if ask_yes_no(msg, args.answer_yes):
            resp = client.physical_devices.delete(results)
            check_resp(resp)
    except NoResultFound:
        LOG.info('Nothing to do.')

def import_physical_device(args, client):
    '''Import physical_devices from a csv file.'''

    LOG.info('Beginning physical_device import from file: {0}'.format(args.physical_device_import))
    LOG.debug('action_command is: {0}'.format(args.action_command))
    LOG.debug('object_type is: {0}'.format(args.object_type))

    failures = []
    overall_exit = 0
    try:
        with open(args.physical_device_import) as csv_file:
            field_names = [
                'serial_number',
                'physical_location',
                'physical_rack',
                'physical_elevation',
                'mac_address_1',
                'mac_address_2',
                'hardware_profile',
                'oob_ip_address',
                'oob_mac_address',
            ]
            device_import = csv.DictReader(csv_file, delimiter=',', fieldnames=field_names)
            for count, row in enumerate(device_import):
                if row['serial_number'].startswith('#'):
                    continue
                LOG.info('Processing row: {0}...'.format(count))

                row = check_null_fields(row, field_names)
                LOG.debug(json.dumps(row, indent=4, sort_keys=True))

                resp = create_physical_device(args, client, device=row)
                LOG.debug(json.dumps(resp, indent=4, sort_keys=True))

                try:
                    resp['http_status']['row'] = row
                    resp['http_status']['row_number'] = count
                    failures.append(resp['http_status'])
                except KeyError:
                    pass

        if failures:
            overall_exit = 1
            LOG.error('The following rows were unable to be processed:')
            for fail in failures:
                LOG.error('    Row: {0} Data: {1} Error: {2}'.format(fail['row_number'],
                                                                     fail['row'],
                                                                     fail['message'],))

        LOG.info('physical_device import complete')
        sys.exit(overall_exit)

    except IOError as ex:
        LOG.error(ex)

def check_null_fields(row, field_names):
    '''Checks for keys will null values and removes them. This allows the API
    to return appropriate errors for keys that require a value.'''

    for key in field_names:
        if not row[key]:
            del row[key]
    return row

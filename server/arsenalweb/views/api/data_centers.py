'''Arsenal API data_centers.'''
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
import logging
from datetime import datetime
from pyramid.view import view_config
from sqlalchemy.orm.exc import NoResultFound
from arsenalweb.views import (
    get_authenticated_user,
    )
from arsenalweb.views.api.common import (
    api_200,
    api_400,
    api_404,
    api_500,
    api_501,
    collect_params,
    )
from arsenalweb.models.common import (
    DBSession,
    )
from arsenalweb.models.data_centers import (
    DataCenter,
    DataCenterAudit,
    )

LOG = logging.getLogger(__name__)


# Functions
def find_data_center_by_name(name):
    '''Find a data_center by name. Returns a data_center object if found,
    raises NoResultFound otherwise.'''

    LOG.debug('Searching for datacenter by name: {0}'.format(name))
    data_center = DBSession.query(DataCenter)
    data_center = data_center.filter(DataCenter.name == name)

    return data_center.one()

def find_data_center_by_id(data_center_id):
    '''Find a data_center by id.'''

    LOG.debug('Searching for datacenter by id: {0}'.format(data_center_id))
    data_center = DBSession.query(DataCenter)
    data_center = data_center.filter(DataCenter.id == data_center_id)

    return data_center.one()

def create_data_center(name=None, updated_by=None, **kwargs):
    '''Create a new data_center.

    Required params:

    name      : A string that is the name of the datacenter.
    updated_by: A string that is the user making the update.

    Optional kwargs:

    provider    : A string that is the datacenter provider.
    address_1   : A string that is the address line 1.
    address_2   : A string that is the address line 2.
    city        : A string that is the address city.
    admin_area  : A string that is the state/province.
    country     : A string that is teh country.
    postal_code : A string that is the postal code.
    contact_name: A string that is the contat name of the data center.
    phone_number: A string that is the phone mumbe rof the data center.
    '''

    try:
        LOG.info('Creating new data_center name: {0}'.format(name))

        utcnow = datetime.utcnow()

        data_center = DataCenter(name=name,
                                 updated_by=updated_by,
                                 created=utcnow,
                                 updated=utcnow,
                                 **kwargs)

        DBSession.add(data_center)
        DBSession.flush()

        audit = DataCenterAudit(object_id=data_center.id,
                                field='name',
                                old_value='created',
                                new_value=data_center.name,
                                updated_by=updated_by,
                                created=utcnow)
        DBSession.add(audit)
        DBSession.flush()

        return data_center
    except Exception as ex:
        msg = 'Error creating new data_center name: {0} exception: {1}'.format(name,
                                                                               ex)
        LOG.error(msg)
        return api_500(msg=msg)

def update_data_center(data_center, **kwargs):
    '''Update an existing data_center.

    Required params:

    data_center: A string that is the user making the update.
    updated_by : A string that is the user making the update.

    Optional kwargs:

    provider    : A string that is the datacenter provider.
    address_1   : A string that is the address line 1.
    address_2   : A string that is the address line 2.
    city        : A string that is the address city.
    admin_area  : A string that is the state/province.
    country     : A string that is teh country.
    postal_code : A string that is the postal code.
    contact_name: A string that is the contat name of the data center.
    phone_number: A string that is the phone mumbe rof the data center.
    '''

    try:
        # Convert everything that is defined to a string.
        my_attribs = kwargs.copy()
        for my_attr in my_attribs:
            if my_attribs.get(my_attr):
                my_attribs[my_attr] = str(my_attribs[my_attr])

        LOG.info('Updating data_center: {0}'.format(data_center.name))

        utcnow = datetime.utcnow()

        for attribute in my_attribs:
            if attribute == 'name':
                LOG.debug('Skipping update to data_center.name.')
                continue
            old_value = getattr(data_center, attribute)
            new_value = my_attribs[attribute]

            if old_value != new_value and new_value:
                if not old_value:
                    old_value = 'None'

                LOG.debug('Updating data_center: {0} attribute: '
                          '{1} new_value: {2}'.format(data_center.name,
                                                      attribute,
                                                      new_value))
                audit = DataCenterAudit(object_id=data_center.id,
                                        field=attribute,
                                        old_value=old_value,
                                        new_value=new_value,
                                        updated_by=my_attribs['updated_by'],
                                        created=utcnow)
                DBSession.add(audit)
                setattr(data_center, attribute, new_value)

        DBSession.flush()

        return data_center

    except Exception as ex:
        msg = 'Error updating data_center name: {0} provider: {1} ' \
              'address_1: {2} address_2: {3} city: {4} admin_area: ' \
              '{5} country: {6} postal_code: {7} contact_name: {8} ' \
              'phone_number: {9} updated_by: {10} exception: ' \
              '{11}'.format(data_center.name,
                            my_attribs['provider'],
                            my_attribs['address_1'],
                            my_attribs['address_2'],
                            my_attribs['city'],
                            my_attribs['admin_area'],
                            my_attribs['country'],
                            my_attribs['postal_code'],
                            my_attribs['contact_name'],
                            my_attribs['phone_number'],
                            my_attribs['updated_by'],
                            repr(ex))
        LOG.error(msg)
        raise

# Routes
@view_config(route_name='api_data_centers', request_method='GET', request_param='schema=true', renderer='json')
def api_data_centers_schema(request):
    '''Schema document for the data_centers API.'''

    data_centers = {
    }

    return data_centers

@view_config(route_name='api_data_centers', permission='data_center_write', request_method='PUT', renderer='json')
def api_data_centers_write(request):
    '''Process write requests for /api/data_centers route.'''

    try:
        req_params = [
            'name',
        ]
        opt_params = [
            'provider',
            'address_1',
            'address_2',
            'city',
            'admin_area',
            'country',
            'postal_code',
            'contact_name',
            'phone_number',
        ]
        params = collect_params(request, req_params, opt_params)

        LOG.debug('Searching for data_center name: {0}'.format(params['name']))

        try:
            data_center = find_data_center_by_name(params['name'])
            update_data_center(data_center, **params)
        except NoResultFound:
            data_center = create_data_center(**params)

        return data_center

    except Exception as ex:
        msg = 'Error writing to data_centers API: {0} exception: {1}'.format(request.url, ex)
        LOG.error(msg)
        return api_500(msg=msg)

@view_config(route_name='api_data_center_r', permission='data_center_delete', request_method='DELETE', renderer='json')
@view_config(route_name='api_data_center_r', permission='data_center_write', request_method='PUT', renderer='json')
def api_data_center_write_attrib(request):
    '''Process write requests for the /api/data_centers/{id}/{resource} route.'''

    resource = request.matchdict['resource']
    payload = request.json_body
    auth_user = get_authenticated_user(request)

    LOG.debug('Updating {0}'.format(request.url))

    # First get the data_center, then figure out what to do to it.
    data_center = find_data_center_by_id(request.matchdict['id'])
    LOG.debug('data_center is: {0}'.format(data_center))

    # List of resources allowed
    resources = [
        'nothing_yet',
    ]

    # There's nothing to do here yet. Maye add updates to existing datacenters?
    if resource in resources:
        try:
            actionable = payload[resource]
        except KeyError:
            msg = 'Missing required parameter: {0}'.format(resource)
            return api_400(msg=msg)
        except Exception as ex:
            LOG.error('Error updating data_centers: {0} exception: {1}'.format(request.url, ex))
            return api_500(msg=str(ex))
    else:
        return api_501()

    return resp

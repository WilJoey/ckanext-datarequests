# -*- coding: utf-8 -*-

# Copyright (c) 2015 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Data Requests Extension.

# CKAN Data Requests Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Data Requests Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Data Requests Extension. If not, see <http://www.gnu.org/licenses/>.

import ckan.lib.base as base
import ckan.model as model
import ckan.plugins as plugins
import ckan.lib.helpers as helpers
import ckanext.datarequests.constants as constants
import functools

from ckan.common import request
from urllib import urlencode

tk = plugins.toolkit
c = tk.c


def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v))
            for k, v in params]


def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)


def search_url(params):
    url = helpers.url_for(controller='ckanext.datarequests.controllers.ui_controller:DataRequestsUI',
                          action='index')
    return url_with_params(url, params)

def org_datarequest_url(params, id):
    url = helpers.url_for(controller='ckanext.datarequests.controllers.ui_controller:DataRequestsUI',
                          action='organization_datarequests', id=id)
    return url_with_params(url, params)

class DataRequestsUI(base.BaseController):

    def _get_context(self):
        return {'model': model, 'session': model.Session,
                'user': c.user, 'auth_user_obj': c.userobj}

    def _show_index(self, organization_id, include_organization_facet, url_func, file_to_render):

        def pager_url(q=None, page=None):
            params = list()
            params.append(('page', page))
            return url_func(params)

        try:
            context = self._get_context()
            page = int(request.GET.get('page', 1))
            limit = constants.DATAREQUESTS_PER_PAGE
            offset = (page - 1) * constants.DATAREQUESTS_PER_PAGE
            data_dict = {'offset': offset, 'limit': limit}

            state = request.GET.get('state', None)
            if state:
                data_dict['closed'] = True if state == 'closed' else False

            if organization_id:
                data_dict['organization_id'] = organization_id

            tk.check_access(constants.DATAREQUEST_INDEX, context, data_dict)
            datarequests_list = tk.get_action(constants.DATAREQUEST_INDEX)(context, data_dict)
            c.datarequest_count = datarequests_list['count']
            c.datarequests = datarequests_list['result']
            c.search_facets = datarequests_list['facets']
            c.page = helpers.Page(
                collection=datarequests_list['result'],
                page=page,
                url=pager_url,
                item_count=datarequests_list['count'],
                items_per_page=limit
            )
            c.facet_titles = {
                'state': tk._('State'),
            }

            # Organization facet cannot be shown when the user is viewing an org
            if include_organization_facet is True:
                c.facet_titles['organization'] = tk._('Organizations')

            return tk.render(file_to_render)
        except ValueError:
            # This exception should only occur if the page value is not valid
            tk.abort(400, tk._('"page" parameter must be an integer'))
        except tk.NotAuthorized:
            tk.abort(401, tk._('Unauthorized to list Data Requests'))

    def index(self):
        return self._show_index(request.GET.get('organization', ''), True, search_url, 'datarequests/index.html')

    def _process_post(self, action, context):
        # If the user has submitted the form, the data request must be created
        if request.POST:
            data_dict = {}
            data_dict['title'] = request.POST.get('title', '')
            data_dict['description'] = request.POST.get('description', '')
            data_dict['organization_id'] = request.POST.get('organization_id', '')

            if action == constants.DATAREQUEST_UPDATE:
                data_dict['id'] = request.POST.get('id', '')

            try:
                result = tk.get_action(action)(context, data_dict)
                tk.response.status_int = 302
                tk.response.location = '/%s/%s' % (constants.DATAREQUESTS_MAIN_PATH,
                                                  result['id'])

            except tk.ValidationError as e:
                # Fill the fields that will display some information in the page
                c.datarequest = {
                    'id': data_dict.get('id', ''),
                    'title': data_dict.get('title', ''),
                    'description': data_dict.get('description', ''),
                    'organization_id': data_dict.get('organization_id', '')
                }
                c.errors = e.error_dict
                c.errors_summary = {}

                for key, error in c.errors.items():
                    c.errors_summary[key] = ', '.join(error)

    def new(self):
        context = self._get_context()

        # Basic intialization
        c.datarequest = {}
        c.errors = {}
        c.errors_summary = {}

        # Check access
        try:
            tk.check_access(constants.DATAREQUEST_CREATE, context, None)
            self._process_post(constants.DATAREQUEST_CREATE, context)

            # The form is always rendered
            return tk.render('datarequests/new.html')

        except tk.NotAuthorized:
            tk.abort(401, tk._('Unauthorized to create a Data Request'))

    def show(self, id):
        data_dict = {'id': id}
        context = self._get_context()

        try:
            tk.check_access(constants.DATAREQUEST_SHOW, context, data_dict)
            c.datarequest = tk.get_action(constants.DATAREQUEST_SHOW)(context, data_dict)

            # Very slow request. It takes two seconds
            try:
                c.datarequest['user'] = tk.get_action('user_show')(context, {'id': c.datarequest['user_id']})
            except tk.ObjectNotFound:
                pass

            if c.datarequest['organization_id']:
                try:
                    organization_show = tk.get_action('organization_show')
                    c.datarequest['organization'] = organization_show(context, {'id': c.datarequest['organization_id']})
                except tk.ObjectNotFound:
                    pass

            if c.datarequest['accepted_dataset']:
                try:
                    package_show = tk.get_action('package_show')
                    c.datarequest['accepted_dataset'] = package_show(context, {'id': c.datarequest['accepted_dataset']})
                except tk.ObjectNotFound:
                    pass

            return tk.render('datarequests/show.html')
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Data Request %s not found') % id)
        except tk.NotAuthorized:
            tk.abort(401, tk._('You are not authorized to view the Data Request %s'
                               % id))

    def update(self, id):
        data_dict = {'id': id}
        context = self._get_context()

        # Basic intialization
        c.datarequest = {}
        c.errors = {}
        c.errors_summary = {}

        try:
            tk.check_access(constants.DATAREQUEST_UPDATE, context, data_dict)
            c.datarequest = tk.get_action(constants.DATAREQUEST_SHOW)(context, data_dict)
            c.original_title = c.datarequest.get('title')
            self._process_post(constants.DATAREQUEST_UPDATE, context)
            return tk.render('datarequests/edit.html')
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Data Request %s not found') % id)
        except tk.NotAuthorized:
            tk.abort(401, tk._('You are not authorized to update the Data Request %s'
                               % id))

    def delete(self, id):
    	data_dict = {'id': id}
    	context = self._get_context()

    	try:
            tk.check_access(constants.DATAREQUEST_DELETE, context, data_dict)
            datarequest = tk.get_action(constants.DATAREQUEST_DELETE)(context, data_dict)
            tk.response.status_int = 302
            tk.response.location = '/%s' % constants.DATAREQUESTS_MAIN_PATH
            helpers.flash_notice(tk._('Data Request %s deleted correctly') % datarequest.get('title', ''))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Data Request %s not found') % id)
        except tk.NotAuthorized:
            tk.abort(401, tk._('You are not authorized to delete the Data Request %s'
                               % id))

    def organization_datarequests(self, id):
        context = self._get_context()
        c.group_dict = tk.get_action('organization_show')(context, {'id': id})
        url_func = functools.partial(org_datarequest_url, id=id)
        return self._show_index(id, False, url_func, 'organization/datarequests.html')

    def close(self, id):
        data_dict = {'id': id}
        context = self._get_context()

        # Basic intialization
        c.datarequest = {}

        def _return_page(errors={}, errors_summary={}):
            # Get datasets (if the data req belongs to an organization, only the one that
            # belongs to the organization are shown)
            organization_id = c.datarequest.get('organization_id', '')
            if organization_id:
                base_datasets = tk.get_action('organization_show')({'ignore_auth': True}, {'id': organization_id})['packages']
            else:
                # FIXME: At this time, only the 500 last modified/created datasets are retrieved.
                # We assume that a user will close their data request with a recently added or modified dataset
                # In the future, we should fix this with an autocomplete form...
                base_datasets = tk.get_action('package_search')({'ignore_auth': True}, {'rows': 500})['results']

            c.datasets = []
            c.errors = errors
            c.errors_summary = errors_summary
            for dataset in base_datasets:
                c.datasets.append({'name': dataset.get('name'), 'title': dataset.get('title')})

            return tk.render('datarequests/close.html')

        try:
            tk.check_access(constants.DATAREQUEST_CLOSE, context, data_dict)
            c.datarequest = tk.get_action(constants.DATAREQUEST_SHOW)(context, data_dict)

            if request.POST:
                data_dict = {}
                data_dict['accepted_dataset'] = request.POST.get('accepted_dataset', None)
                data_dict['id'] = id

                tk.get_action(constants.DATAREQUEST_CLOSE)(context, data_dict)
                tk.response.status_int = 302
                tk.response.location = '/%s/%s' % (constants.DATAREQUESTS_MAIN_PATH, data_dict['id'])
            else: # GET
                return _return_page()

        except tk.ValidationError as e:     # Accepted Dataset is not valid
            errors_summary = {}
            for key, error in e.error_dict.items():
                errors_summary[key] = ', '.join(error)

            return _return_page(e.error_dict, errors_summary)
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Data Request %s not found') % id)
        except tk.NotAuthorized:
            tk.abort(401, tk._('You are not authorized to close the Data Request %s'
                               % id))

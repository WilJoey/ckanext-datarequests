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

import constants
from ckan.plugins import toolkit as tk


def datarequest_create(context, data_dict):
    return {'success': True}


@tk.auth_allow_anonymous_access
def datarequest_show(context, data_dict):
    return {'success': True}


def auth_if_creator(context, data_dict):
    # Sometimes data_dict only contains the 'id'
    if 'user_id' not in data_dict:
        datareq_show = tk.get_action(constants.DATAREQUEST_SHOW)
        data_dict = datareq_show({'ignore_auth': True}, {'id': data_dict.get('id')})

    return {'success': data_dict['user_id'] == context.get('auth_user_obj').id}


def datarequest_update(context, data_dict):
	return auth_if_creator(context, data_dict)


@tk.auth_allow_anonymous_access
def datarequest_index(context, data_dict):
    return {'success': True}


def datarequest_delete(context, data_dict):
	return auth_if_creator(context, data_dict)


def datarequest_close(context, data_dict):
    return auth_if_creator(context, data_dict)

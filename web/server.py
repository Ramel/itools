# -*- coding: UTF-8 -*-
# Copyright (C) 2005-2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2006-2007 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2007-2008 Henry Obein <henry@itaapy.com>
# Copyright (C) 2008 David Versmisse <david.versmisse@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from warnings import warn

# Import from itools
from itools.http import Redirection, ClientError, ServerError
from itools.log import log_error
from itools.uri import Reference
from context import WebContext
from exceptions import FormError



status2name = {
    401: 'http_unauthorized',
    403: 'http_forbidden',
    404: 'http_not_found',
    405: 'http_method_not_allowed',
    409: 'http_conflict'}


def find_view_by_method(server, context):
    """Associating an uncommon HTTP or WebDAV method to a special view.
    method "PUT" -> view "http_put" <instance of view>
    """
    method_name = context.request.method
    view_name = "http_%s" % method_name.lower()
    context.view = context.resource.get_view(view_name)
    if context.view is None:
        raise ServerError(501)


class RequestMethod(object):

    @classmethod
    def check_cache(cls, server, context):
        """Implement cache if your method supports it.
        Most methods don't, hence the default implementation.
        """
        pass


    @classmethod
    def check_conditions(cls, server, context):
        """Check conditions to match before the response can be processed:
        resource, state, request headers...
        """
        pass


    @classmethod
    def check_transaction(cls, server, context):
        """Return True if your method is supposed to change the state.
        """
        raise NotImplementedError


    @classmethod
    def commit_transaction(cls, server, context):
        database = server.database
        # Check conditions are met
        if cls.check_transaction(server, context) is False:
            database.abort_changes()
            return

        # Save changes
        try:
            database.save_changes()
        except Exception:
            cls.internal_server_error(server, context)


    @classmethod
    def set_body(cls, server, context):
        response = context.response
        body = context.entity
        if isinstance(body, Reference):
            reference = context.uri.resolve(body)
            response.redirect(reference, 302)
            return
        response.set_body(body)
        length = response.get_content_length()
        response.set_header('content-length', length)


    @classmethod
    def internal_server_error(cls, server, context):
        log_error('Internal Server Error', domain='itools.web')
        context.status = 500
        root = context.site_root
        context.entity = root.http_internal_server_error.GET(root, context)


    @classmethod
    def handle_request(cls, server, request):
        # Make the context
        context = WebContext(request)

        # (1) Find out the requested resource and view
        response = context.response
        root = context.site_root
        try:
            # Check the client's cache
            cls.check_cache(server, context)
            # Check pre-conditions
            cls.check_conditions(server, context)
        except ClientError, error:
            status = error.status
            context.status = status
            context.view_name = status2name[status]
            context.view = root.get_view(context.view_name)
        except Redirection:
            response.set_status(error.status)
            response.set_header('content-length', 0)
            response.set_body(None)
            return response

        # (2) Always deserialize the query
        resource = context.resource
        view = context.view
        try:
            context.query = view.get_query(context)
        except FormError, error:
            context.method = view.on_query_error
            context.query_error = error
        except Exception:
            cls.internal_server_error(server, context)
            context.method = None
        else:
            # GET, POST...
            context.method = getattr(view, cls.method_name)

        # (3) Render
        try:
            m = getattr(root.http_main, cls.method_name)
            context.entity = m(root, context)
        except Exception:
            cls.internal_server_error(server, context)
        else:
            # Ok: set status
            if context.status is not None:
                pass
            elif isinstance(context.entity, Reference):
                context.status = 302
            elif context.entity is None:
                context.status = 204
            else:
                context.status = 200

        # (4) Commit the transaction
        cls.commit_transaction(server, context)

        # (5) Build and return the response
        response.set_status(context.status)
        cls.set_body(server, context)

        # (6) Ok
        return response



class GET(RequestMethod):

    method_name = 'GET'


    @classmethod
    def check_cache(cls, server, context):
        # Get the resource's modification time
        resource = context.resource
        mtime = context.view.get_mtime(resource)
        if mtime is None:
            return

        # Set the last-modified header
        mtime = mtime.replace(microsecond=0)
        context.response.set_header('last-modified', mtime)

        # Check for the request header If-Modified-Since
        if_modified_since = context.request.get_header('if-modified-since')
        if if_modified_since is None:
            return

        # Cache: check modification time
        if mtime <= if_modified_since:
            raise Redirection(304)


    @classmethod
    def check_transaction(cls, server, context):
        # GET is not expected to change the state
        if getattr(context, 'commit', False) is True:
            # FIXME To be removed one day.
            warn("Use of 'context.commit' is strongly discouraged.")
            return True
        return False



class POST(RequestMethod):

    method_name = 'POST'


    @classmethod
    def check_transaction(cls, server, context):
        return getattr(context, 'commit', True) and context.status < 400



class DELETE(RequestMethod):

    method_name = 'DELETE'


    @classmethod
    def find_view(cls, server, context):
        # Look for the "delete" view
        return find_view_by_method(server, context)


    @classmethod
    def check_conditions(cls, server, context):
        resource = context.resource
        parent = resource.parent
        # The root cannot delete itself
        if parent is None:
            raise ClientError(405)


    @classmethod
    def check_transaction(cls, server, context):
        return getattr(context, 'commit', True) and context.status < 400

#! /usr/bin/env python

from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import json
import logging
import os
import random
import string
import time

import django
import redis
from cwt.wps_lib import metadata
from cwt.wps_lib import operations
from django.contrib.auth import models as dj_models
from lxml import etree

from wps import models
from wps import tasks
from wps import settings as local_settings
from wps.conf import settings

logger = logging.getLogger(__name__)

class NodeManagerError(Exception):
    pass

class NodeManager(object):

    def initialize(self):
        """ Initialize node_manager

        Only run if WPS_NO_INIT is not set.
        """
        if os.getenv('WPS_NO_INIT') is not None:
            return

        logger.info('Initializing node manager')

        try:
            server = models.Server.objects.get(host='default')
        except models.Server.DoesNotExist:
            logger.info('Default server does not exist, creating new server entry.')

            server = models.Server(host='default')

            server.save()
        except django.db.utils.ProgrammingError:
            logger.info('Database has not been initialized yet.')

            return

        servers = models.Server.objects.all()

        for s in servers:
            if s.capabilities == '':
                logger.info('Server "%s" capabilities have not been populated', s.host)

                tasks.capabilities.delay(server.id)

    def create_user(self, openid_url, token):
        """ Create a new user. """
        user = dj_models.User() 

        user.username = openid_url

        try:
            user.save()
        except django.db.IntegrityError as e:
            raise NodeManagerError('Failed to create user: {}'.format(e.message))

        oauth2 = models.OAuth2()

        oauth2.user = user
        oauth2.openid = openid_url
        oauth2.token_type = token['token_type']
        oauth2.refresh_token = token['refresh_token']
        oauth2.access_token = token['access_token']
        oauth2.scope = json.dumps(token['scope'])
        oauth2.expires_at = datetime.datetime.fromtimestamp(token['expires_at'])
        oauth2.api_key = ''.join(random.choice(string.ascii_letters+string.digits) for _ in xrange(64))

        oauth2.save()

        return user.oauth2.api_key

    def create_wps_exception(self, ex_type, message):
        """ Create an ExceptionReport. """
        ex_report = metadata.ExceptionReport(settings.WPS_VERSION)

        ex_report.add_exception(ex_type, message)

        return NodeManagerError(ex_report.xml())

    def get_parameter(self, params, name):
        """ Gets a parameter from a django QueryDict """

        # Case insesitive
        temp = dict((x.lower(), y) for x, y in params.iteritems())

        if name.lower() not in temp:
            logger.info('Missing required parameter %s', name)

            raise self.create_wps_exception(
                    metadata.MissingParameterValue,
                    name)

        return temp[name.lower()]

    def get_status(self, job_id):
        """ Get job status. """
        try:
            job = models.Job.objects.get(pk=job_id)
        except models.Job.DoesNotExist:
            raise self.create_wps_exception(
                    metadata.NoApplicableCode,
                    'Job with id {0} does not exist'.format(job_id))

        try:
            latest_status = job.status_set.all().latest('created_date')
        except models.Status.DoesNotExist:
            raise NodeManagerError('Job {0} has not states'.format(job_id))

        return latest_status.result

    def get_instance(self):
        """ Determine which CDAS instance to execute on. """
        instances = models.Instance.objects.all()

        if len(instances) == 0:
            raise self.create_wps_exception(
                    metadata.NoApplicableCode,
                    'No CDAS2 instances are available')

        return instances[0]

    def handle_get_capabilities(self):
        """ Handles get_capabilities operation. """
        logger.info('Handling GetCapabilities request')

        try:
            server = models.Server.objects.get(host='default')
        except models.Server.DoesNotExist:
            raise self.create_wps_exception(
                    metadata.NoApplicableCode,
                    'Default server has not been created yet')

        if server.capabilities == '':
            raise self.create_wps_exception(
                    metadata.NoApplicableCode,
                    'Servers capabilities have not been populated yet, server may still be starting up')

        return server.capabilities

    def handle_describe_process(self, identifier):
        """ Handles describe_process operation. """
        logger.info('Handling DescribeProcess request')
        
        try:
            process = models.Process.objects.get(identifier=identifier)
        except models.Process.DoesNotExist:
            raise self.create_wps_exception(
                    metadata.NoApplicableCode,
                    'Process {0} does not exist'.format(identifier))

        return process.description

    def handle_execute(self, identifier, data_inputs):
        """ Handles execute operation """
        logger.info('Handling Execute request')

        instance = self.get_instance()

        logger.info('Executing on CDAS2 instance %s:%s', instance.host, instance.request)

        hostname = local_settings.HOSTNAME

        port = local_settings.PORT

        task = tasks.execute.delay(instance.id, identifier, data_inputs, hostname, port)

        response = task.get()

        return response

    def handle_get(self, params):
        """ Handle an HTTP GET request. """
        logger.info('Received GET request %s', params)
        
        request = self.get_parameter(params, 'request')

        service = self.get_parameter(params, 'service')

        request = request.lower()

        if request == 'getcapabilities':
            response = self.handle_get_capabilities()
        elif request == 'describeprocess':
            identifier = self.get_parameter(params, 'identifier')

            response = self.handle_describe_process(identifier)
        elif request == 'execute':
            identifier = self.get_parameter(params, 'identifier')

            data_inputs = self.get_parameter(params, 'datainputs')

            response = self.handle_execute(identifier, data_inputs)

        return response

    def handle_post(self, data):
        """ Handle an HTTP POST request. 

        NOTE: we only support execute requests as POST for the moment
        """
        logger.info('Received POST request %s', data)

        try:
            request = operations.ExecuteRequest.from_xml(data)
        except etree.XMLSyntaxError:
            logger.exception('Failed to parse xml request')

            raise self.create_wps_exception(
                    metadata.NoApplicableCode,
                    'POST request only supported for Execute operation')

        # Build to format [variable=[];domain=[];operation=[]]
        data_inputs = '[{0}]'.format(
                ';'.join('{0}={1}'.format(x.identifier, x.data.value)
                    for x in request.data_inputs))

        # CDAS doesn't like single quotes
        data_inputs = data_inputs.replace('\'', '\"')

        response = self.handle_execute(request.identifier, data_inputs)
        
        return response

    def handle_request(self, request):
        """ Handle HTTP request """
        if request.method == 'GET':
            return self.handle_get(request.GET)
        elif request.method == 'POST':
            return self.handle_post(request.body)

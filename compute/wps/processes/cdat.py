#! /usr/bin/env python

import os
import re
import uuid
from contextlib import closing
from contextlib import nested

import cdms2
import cwt
import dask.array as da
import numpy as np
from celery import shared_task
from celery.utils.log import get_task_logger
from dask import delayed

from wps import models
from wps import settings
from wps.processes import process
from wps.processes import cwt_shared_task
from wps.processes import register_process

logger = get_task_logger('wps.processes.cdat')

__all__ = ['avg']

def sort_inputs_by_time(variables):
    input_dict = {}
    time_pattern = '.*_(\d+)-(\d+)\.nc'

    for v in variables:
        result = re.search(time_pattern, v.uri)

        start, _ = result.groups()

        input_dict[start] = v

    sorted_keys = sorted(input_dict.keys())

    return [input_dict[x] for x in sorted_keys]

@register_process('CDAT.subset')
@cwt_shared_task()
def subset(self, variables, operations, domains, **kwargs):
    self.PUBLISH = process.ALL

    user, job = self.initialize(credentials=True, **kwargs)

    job.started()

    v, d, o = self.load(variables, domains, operations)

    op = self.op_by_id('CDAT.subset', o)

    inputs = sort_inputs_by_time(op.inputs)

    grid, tool, method = self.generate_grid(op, v, d)

    def post_process(data):
        if grid is not None:
            data = data.regrid(grid, regridTool=tool, regridMethod=method)

        return data

    output_path = self.retrieve_variable([inputs[0]], op.domain, job, post_process=post_process)

    output_url = self.generate_output_url(output_path, **kwargs)

    output_var = cwt.Variable(output_url, inputs[0].var_name)

    return output_var.parameterize()

@register_process('CDAT.aggregate')
@cwt_shared_task()
def aggregate(self, variables, operations, domains, **kwargs):
    self.PUBLISH = process.ALL

    user, job = self.initialize(credentials=True, **kwargs)

    job.started()

    v, d, o = self.load(variables, domains, operations)

    op = self.op_by_id('CDAT.aggregate', o)

    inputs = sort_inputs_by_time(op.inputs)

    grid, tool, method = self.generate_grid(op, v, d)

    def post_process(data):
        if grid is not None:
            data = data.regrid(grid, regridTool=tool, regridMethod=method)

        out.write(data, id=var_name)

    output_path = self.retrieve_variable(inputs, op.domain, job, post_process=post_process)

    output_url = self.generate_output_url(output_path, **kwargs)

    output_var = cwt.Variable(output_url, inputs[0].var_name)

    return output_var.parameterize()

@cwt_shared_task()
def avg(self, variables, operations, domains, **kwargs):
    self.PUBLISH = process.ALL

    job, status = self.initialize(credentials=True, **kwargs)

    v, d, o = self.load(variables, domains, operations)

    op = self.op_by_id('CDAT.avg', o)

    out_local_path = self.generate_local_output()

    if len(op.inputs) == 1:
        input_var = op.inputs[0]

        var_name = input_var.var_name

        input_file = self.cache_input(input_var, op.domain)

        axes = op.get_parameter('axes', True)

        if axes is None:
            raise Exception('axes parameter was not defined')

        with input_file as input_file:
            axis_indexes = [input_file[var_name].getAxisIndex(x) for x in axes.values]

            if any(x == -1 for x in axis_indexes):
                truth = zip(axes.values, [True if x != -1 else False
                                          for x in axis_indexes])

                raise Exception('An axis does not exist {}'.format(truth))

            shape = input_file[var_name].shape

            chunk = [shape[0] / 10] + list(shape[1:])

            chunk = tuple(chunk)

            mean = da.from_array(input_file[var_name], chunks=chunk)

            for axis in axis_indexes:
                mean = mean.mean(axis=axis)

            result = mean.compute()

            axes = [x for x in input_file.axes.values() if x.id not in axes.values and x.id != 'bound']

            with cdms2.open(out_local_path, 'w') as output_file:
                output_file.write(result, id=var_name, axes=axes)
    else:
        raise Exception('Average between multiple files is not supported yet.')

    out_path = self.generate_output(out_local_path, **kwargs)

    out_var = cwt.Variable(out_path, var_name)

    return out_var.parameterize()

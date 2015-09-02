import sys, traceback

from modules.utilities import *
from datacache.manager import dataManager, CachedVariable
from datacache.domains import Region
from request.manager import TaskRequest

class KernelManager:

    def getKernelInputs( self, operation, request ):
        read_start_time = time.time()
        use_cache =  request['cache']
        data = request.data.value
        region = request.region.value
        cache_type = CachedVariable.getCacheType( use_cache, operation )
        if cache_type == CachedVariable.CACHE_OP:
            dslice = operation.get('slice',None)
            if dslice: region = Region( region, slice=dslice )
        variable, result_obj = dataManager.loadVariable( data, region, cache_type )
        cached_region = Region( result_obj['region'] )
        if cached_region <> region:
            subset_args = region.toCDMS()
            subset_var = numpy.ma.fix_invalid( variable( **subset_args ) )
#            wpsLog.debug( " $$$ Subsetting variable: args = %s\n >> in = %s\n >> out = %s " % ( str(subset_args), str(variable.squeeze().tolist()), str(subset_var.squeeze().tolist()) ))
            variable = subset_var
        data['variables'] = [ variable ]
        data['result'] = result_obj
        read_end_time = time.time()
        wpsLog.debug( " $$$ DATA READ Complete (domain = %s): %s " % ( str(region), str(read_end_time-read_start_time) ) )
        return data, region

    def run( self, task_request ):
        results = []
        wpsLog.debug( "---"*50 + "\n $$$ Kernel Manager START NEW TASK: request = %s \n" % str(task_request) )
        start_time = time.time()
        try:
            operations =  task_request.operations
            operations_list = [None] if (operations.value is None) else operations.values
            for operation in operations_list:
                data, region = self.getKernelInputs( operation, task_request )
                kernel = self.getKernel( operation )
                result = kernel.run( data, region, operation ) if kernel else { 'result': data['result'] }
                results.append( result )
            end_time = time.time()
            wpsLog.debug( " $$$ Kernel Execution Complete, total time = %.2f " % (end_time-start_time) )
        except Exception, err:
            wpsLog.debug( " Error executing kernel: %s " % str(err) )
            wpsLog.debug( traceback.format_exc() )
            result = data.get('result', {} )
            result['error'] = str(err)
            results.append( result )
        return results

    def getKernel( self, operation ):
        if operation:
            if operation.get('kernel','base') == 'time':
                from kernels.timeseries_analysis import TimeseriesAnalytics
                return TimeseriesAnalytics()
            else:
                raise Exception( "No compute kernel found for operations %s" % str(operation) )

kernelMgr = KernelManager()

if __name__ == "__main__":
    wpsLog.addHandler( logging.StreamHandler(sys.stdout) ) #logging.FileHandler( os.path.abspath( os.path.join(os.path.dirname(__file__), '..', 'logs', 'wps.log') ) ) )
    wpsLog.setLevel(logging.DEBUG)
    pre_cache = False

    if pre_cache:
        cache_args =  {   'data': {'id': 'hur', 'collection': 'MERRA/mon/atmos'},  'region': {'level': [100000.0]},  }
        kernelMgr.run( TaskRequest( task=cache_args ) )

    task_args =  { 'region': '{"longitude": -137.09327695888, "latitude": 35.487604770915, "level": 85000}',
                  'data': '{"collection": "MERRA/mon/atmos", "id": "hur"}',
                  'operation': '[  {"kernel": "time", "type": "departures",  "bounds":"np"}, '
                                  '{"kernel":"time", "type":"climatology", "bounds":"annualcycle"} ]'  }

    val_task_args =  {  'region': '{"longitude": -137.09327695888, "latitude": 35.487604770915, "level": 85000, "time": "1979-1-16 12:0:0.0" }',
                        'data': '{"collection": "MERRA/mon/atmos", "id": "hur"}',
                        'operation': '{ "kernel": "time", "type": "value" }'  }

    test_task_args1 =  {u'embedded': [u'true'], u'service': [u'WPS'], u'rawDataOutput': [u'result'], u'config': {'cache': True}, u'region': {u'latitude': -4.710426330566406, u'time': u'2010-01-16T12:00:00', u'longitude': -125.875, u'level': 100000}, u'request': [u'Execute'], u'version': [u'1.0.0'], u'operation': [{u'kernel': u'time', u'slice': u't', u'type': u'departures', u'bounds': u'np'}, {u'kernel': u'time', u'slice': u't', u'type': u'climatology', u'bounds': u'annualcycle'}, {u'kernel': u'time', u'type': u'value'}], u'identifier': [u'cdas'], u'data': {u'id': u'hur', u'collection': u'MERRA/mon/atmos'}}
    test_task_args = { 'version': [u'1.0.0'], 'service': [u'WPS'], 'embedded': [u'true'], 'rawDataOutput': [u'result'], 'identifier': [u'cdas'], 'request': [u'Execute'], 'datainputs': [u'[region={"level":"100000"};data={"collection":"MERRA/mon/atmos","id":"hur"};]']}
    kernelMgr.run(  TaskRequest( request=test_task_args ) )

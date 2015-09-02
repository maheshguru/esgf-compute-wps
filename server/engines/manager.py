from modules.module import Executable
from modules.utilities import *
from datacache.manager import CachedVariable
from datacache.status_cache import  StatusCacheManager
from datacache.domains import Domain, Region
from request.manager import TaskRequest
import traceback

StatusCache = StatusCacheManager()

class ComputeEngine( Executable ):

    def __init__( self, id ):
        Executable.__init__( self, id )
        self.communicator = None
        self.cachedVariables = {}
        self.pendingTasks = {}
        self.statusCache = StatusCacheManager()

    def restore(self):
        cache_data = self.statusCache.restore( 'cdas_compute_engine_cache' )
        if cache_data:
            [ self.communicator.worker_stats, self.cachedVariables,  self.pendingTasks ] = cache_data

    def cache(self):
        self.statusCache.cache( 'cdas_compute_engine_cache', [ self.communicator.worker_stats, self.cachedVariables, self.pendingTasks ] )

    def processPendingTasks(self):
        pTasks = str( self.pendingTasks.keys() )
        t0 = time.time()
        completed_requests = []
        do_cache = False
        for task_monitor,cached_domain in self.pendingTasks.items():
            if task_monitor.ready():
                if task_monitor.status() == 'FAILURE':
                    wpsLog.debug( "Task %s(%s) Failed:\n>> '%s' " % ( task_monitor.taskName(), task_monitor.id, str(task_monitor) ) )
                else:
                    results = task_monitor.result()
                    if not results:
                        wpsLog.debug( " ***** Empty cache_request for task '%s', status = '%s':\n %s " % ( task_monitor.id, task_monitor.status(), str(task_monitor) ) )
                    else:
                        worker = results[0]['worker']
                        cached_domain.cacheRequestComplete( worker )
                        completed_requests.append( task_monitor )
                        self.communicator.clearWorkerState( worker )
                        wpsLog.debug( " ***** process Completed Task: worker = %s, cache_request = %s " % ( worker, str(task_monitor) ) )
        for completed_request in completed_requests:
            del self.pendingTasks[ completed_request ]
            do_cache = True
        if do_cache: self.cache()
        t1 = time.time()
        wpsLog.debug( " ***** processPendingTasks[ dt = %0.3f ]: %s" %  ( t1-t0, pTasks ) )


    def findCachedDomain(self, var_cache_id, region, var_specs ):
        cached_var = self.cachedVariables.setdefault( var_cache_id, CachedVariable( id=var_cache_id, specs=var_specs) )
        if ( cached_var is not None ):
            overlap,domain = cached_var.findDomain( region )
            if overlap == Domain.CONTAINED: return cached_var, domain
        return cached_var, None


    def execute( self, task_request, **compute_args ):
        try:
            t0 = time.time()
            async = compute_args.get( 'async', False )
            cache_request = None
            execution_record = {}
            self.communicator.updateWorkerStats()
            self.processPendingTasks()
            designated_worker = None
            wpsLog.debug( " ***** Executing compute engine (t=%.2f), request: %s" % ( t0, str(task_request) ) )
            dset_mdata = task_request.data.values
            op_region = task_request.region.value
            operation = task_request.operations.values

            for var_mdata in dset_mdata:
                id = var_mdata.get('id','')
                collection = var_mdata.get('collection',None)
                url = var_mdata.get('url','')
                var_cache_id = ":".join( [collection,id] ) if (collection is not None) else ":".join( [url,id] )
                if var_cache_id <> ":":
                    cached_var,cached_domain = self.findCachedDomain( var_cache_id, op_region, task_request )
                    if cached_domain is None:
                        cache_axis_list = [Region.LEVEL] if operation else [Region.LEVEL, Region.LATITUDE, Region.LONGITUDE]
                        cache_region = Region( op_region, axes=cache_axis_list )
                        cache_op_args = { 'region':cache_region.spec, 'data':var_mdata.spec }
                        tc0 = time.time()
                        cache_task_request = TaskRequest( task=cache_op_args)
                        cache_worker = self.communicator.getNextWorker()
                        cache_request = self.communicator.submitTask( cache_task_request, cache_worker )
       #                 execution_record['cache'] = cache_region
                        tc01 = time.time()
                        cached_domain = cached_var.addDomain( cache_region )
                        self.pendingTasks[ cache_request ] = cached_domain
                        self.cache()
                        tc1 = time.time()
                        wpsLog.debug( " ***** Caching data [tid:%s] to worker '%s' ([%.2f,%.2f,%.2f] dt = %.3f): args = %s " %  ( cache_request.id, cache_worker, tc0, tc01, tc1, (tc1-tc0), str(cache_op_args) ) )
                    else:
                        worker_id, cache_request_status = cached_domain.getCacheStatus()
                        if (cache_request_status == Domain.COMPLETE) or ( cached_var.cacheType() == CachedVariable.CACHE_OP ):
                            designated_worker = worker_id
                            wpsLog.debug( " ***** Found cached data on worker %s " %  worker_id )
                        else:
                            wpsLog.debug( " ***** Found cache op on worker %s, data not ready " %  worker_id )

            if operation:
                t2 = time.time()

                if designated_worker is None:
                    designated_worker = self.communicator.getNextWorker()
                else:
                    execution_record['designated_worker'] = True

                task_monitor = self.communicator.submitTask( task_request, designated_worker )
                op_domain = cached_var.addDomain( op_region )
                self.pendingTasks[ task_monitor ] = op_domain
                self.cache()

                wpsLog.debug( " ***** Sending operation [tid:%s] to worker '%s' (t = %.2f, dt0 = %.3f): request= %s " %  ( task_monitor.id, str(designated_worker), t2, t2-t0, str(task_request) ) )
                if async: return task_monitor

                result = task_monitor.result(exerec=execution_record)
                t1 = time.time()
                wpsLog.debug( " ***** Retrieved result [tid:%s] from worker '%s' (t = %.2f, dt1 = %.3f)" %  ( task_monitor.id, result[0]['worker'], t1, t1-t2 ) )
                return result

            else:
                if async: return cache_request

        except Exception, err:
            wpsLog.error(" Error running compute engine: %s\n %s " % ( str(err), traceback.format_exc()  ) )
            return err




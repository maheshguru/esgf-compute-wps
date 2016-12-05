import cdms2
from cdms2.selectors import timeslice
import esgf
import os
from pywps import config
import uuid

from wps import logger
from wps.processes import esgf_operation
from wps.processes.esgf_operation import create_from_def

class CDATEnsemble(esgf_operation.ESGFOperation):
    KNOWN_GRIDS = {
        't42': {
            'func': cdms2.createGaussianGrid,
            'args': [128]
        }
    }

    def __init__(self):
        super(CDATEnsemble, self).__init__()

    @property
    def title(self):
        return 'CDAT Ensemble'

    def __call__(self, data_manager, status):
        var = [x for x in self.input() if isinstance(x, esgf.Variable)]

        var_name = None

        if len(var):
            var_name = var[0].var_name

        src = [data_manager.metadata(x) for x in var
               if isinstance(x, esgf.Variable)]

        # Find inputs that are operations and execute them appending the
        # input list
        # NOTE this will be moved into workflow at some point
        input_ops = [x for x in self.input() if isinstance(x, esgf.Operation)]

        for inp in input_ops:
            logger.debug('Executing child operation %s', inp.identifier)

            op = create_from_def(inp)

            if self.domain:
                op.data.domain = self.domain

            op.__call__(data_manager, status)

            src.append(data_manager.metadata(op.output))

            # If we couldn't get the variable name from source files,
            # take the first name from input operation outputs
            if not var_name:
                var_name = op.output.var_name

        # assumed all files are from the same model
        # TODO add some validation
        time = [x.getTime() for x in src]

        temporal, spatial = self._gen_domains(src[0].getAxisList(),
                                              time[0],
                                              self.domain)
        
        logger.debug('Spatial domain %r', spatial)

        start, end, step = self._convert_temporal_domain(time[0], temporal)

        logger.debug('Temporal domain: start=%s stop=%s step=%s', start, end, step)

        new_file_name = '%s.nc' % (str(uuid.uuid4()),)
        new_file_path = config.getConfigValue('server', 'outputPath', '/var/wps')
        new_file = os.path.join(new_file_path, new_file_name)

        logger.debug('Writing file to %s', new_file)

        fout = cdms2.open(new_file, 'w')

        denom = len(src)

        target_grid = None

        gridder = self.parameter('gridder', required=False)

        # Build the target grid if gridder is passed to the operation
        if gridder:
            if isinstance(gridder.grid, esgf.Domain):
                raise esgf.WPSServerError(
                    'Target grid from Domain NotImplemented yet.')
            elif isinstance(gridder.grid, esgf.Variable):
                raise esgf.WPSServerError(
                    'Target grid from Variable NotImplemented yet.')
            elif isinstance(gridder.grid, (str, unicode)):
                try:
                    grid = self.KNOWN_GRIDS[gridder.grid.lower()]
                except KeyError:
                    raise esgf.WPSServerError('Unknown target grid %s' %
                                              (gridder.grid,))

                target_grid = grid['func'](*grid['args'])
            else:
                raise esgf.WPSServerError(
                    'Unknown value passed as target grid %r' % (gridder.grid,))

            logger.debug('Target grid %r', target_grid)

        for i in xrange(start, end, step):
            logger.debug('Averaging time slice %s', i)

            # Grab indexed time slice relative to it's own timeline
            # Apply spatial subset if present
            data = [x(time=time[j][i], **spatial) for j, x in enumerate(src)]

            # Regrid slice
            if target_grid:
                data = [x.regrid(target_grid,
                                 regridTool=gridder.tool,
                                 regridMethod=gridder.method) for x in data]

            data_sum = reduce(lambda x, y: x + y, data)

            data_avg = data_sum / denom

            fout.write(data_avg, id=var_name) 

            del data[:]
            del data_sum
            del data_avg

        fout.close()

        dap_url = self.create_dap_url(new_file_name)

        self.set_output(dap_url, var_name)

    def _convert_temporal_domain(self, time, domain):
        start = 0
        end = len(time)
        step = 1

        if domain:
            if domain.crs == esgf.Dimension.indices:
                start = domain.start
                end = domain.end
                step = domain.step
            elif domain.crs == esgf.Dimension.values:
                # Convert values in indices
                try:
                    start, end = time.mapInterval((str(domain.start),
                                                   str(domain.end)))
                except Exception as e:
                    raise esgf.WPSServerError(
                        'MapInterval failed for time domain "%r" error "%s"' %
                        (domain, e))

                step = domain.step
            else:
                raise esgf.WPSServerError('Unknown CRS for time domain "%r"' %
                                          (domain,))

        return start, end, step

    def _gen_domains(self, axes, time, domain):
        temporal = None
        spatial = {}

        if domain:
            for d in domain.dimensions:
                is_time = False

                # Check if the dimension is temporal
                for a in axes:
                    if (d.name == 'time' or
                            (d.name == a.id and a.isTime())):
                        is_time = True

                        temporal = d

                        break

                # Process spatial dimensions
                if not is_time:
                    if d.crs == esgf.Dimension.indices:
                        spatial[d.name] = slice(d.start, d.end)
                    elif d.crs == esgf.Dimension.values:
                        spatial[d.name] = (d.start, d.end)
                    else:
                        raise esgf.WPSServerError('Unknown CRS value "%s"' %
                                                  (temporal,))
    
        return temporal, spatial

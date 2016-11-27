from .base import fetch_samples
from ..urlio import DataManagementError
import sys
from copy import deepcopy
from pypif import pif
import json
# debugging
import sys
def debug(msg):
    #sys.stdout.write(msg + '\n')
    #sys.stdout.flush()
    pass

def link_factory(projectID,
    host='http://sagittariidae.adapt.mines.edu'):
    debug('entered link factory')
    samples = fetch_samples(host, projectID, refresh=True)
    debug('fetched sample: {}'.format(samples[:5]))
    def adder(pifdata):
        """
        Add a reference to sagittariidae data.
        """
        details = pifdata.preparation[0].details
        # extract fields required to generate the sample name
        plate = [d.scalars for d in details if d.name == 'plate number'][0]
        build = [d.scalars for d in details if d.name == 'build'][0]
        column = [d.scalars for d in details if d.name == 'column'][0]
        row = [d.scalars for d in details if d.name == 'row'][0]
        # sample name
        name = 'P{plate:03d}_B{build:03d}_{column:s}{row:02d}'.format(
            plate=plate, build=build, column=column, row=row)
        # get sample ID
        try:
            sampleID = [s['id'] for s in samples if s['name'] == name][0]
            url = '{host:}/projects/{project:}/samples/{sample:}'.format(
                host=host, project=projectID, sample=sampleID)
            # modify pifdata in place.
            #pdata = deepcopy(pifdata)
            pifdata.sagittariidae = pif.Reference(url=url)
            #return pif.dumps(pdata)
        except IndexError:
            sys.stderr.write('Sample {} was not found. ' \
                             'Skipping.\n'.format(name))
            sys.stderr.flush()
        except Exception:
            sys.stderr.write('Unknown error. Aborting.\n')
            sys.stderr.flush()
            raise
    return adder

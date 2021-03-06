# pyinfra
# File: pyinfra/api/connect.py
# Desc: handle connecting to the inventory

import gevent
import six

from pyinfra.progress import progress_spinner


def connect_all(state):
    '''
    Connect to all the configured servers in parallel. Reads/writes state.inventory.

    Args:
        state (``pyinfra.api.State`` obj): the state containing an inventory to connect to
    '''

    # Don't connect to anything within our (top level, --limit) limit
    hosts = [
        host for host in state.inventory
        if not isinstance(state.limit_hosts, list)
        or host in state.limit_hosts
    ]

    greenlet_to_host = {
        state.pool.spawn(host.connect, state): host
        for host in hosts
    }

    with progress_spinner(greenlet_to_host.values()) as progress:
        for greenlet in gevent.iwait(greenlet_to_host.keys()):
            host = greenlet_to_host[greenlet]
            progress(host)

    # Get/set the results
    failed_hosts = set()

    for greenlet, host in six.iteritems(greenlet_to_host):
        # Raise any unexpected exception
        greenlet.get()

        if host.connection:
            state.activate_host(host)
        else:
            failed_hosts.add(host)

    # Remove those that failed, triggering FAIL_PERCENT check
    state.fail_hosts(failed_hosts, activated_count=len(hosts))

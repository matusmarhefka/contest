#!/usr/bin/python3

import os
import sys
import atexit
from logging import info as log

sys.path.insert(0, '../lib')
import util
import tmt


util.setup_test_logging()
# TODO:
#atexit.register(tmt.pass_on_success)

log("hello from test!")

#import requests
#x = requests.get('https://google.com')
#log(f"got req: {x}")


tmt.report('pass', '/some/result')

tmt.report('fail', '/another/result', logs=['/etc/passwd', '/etc/mtab'], note='foo \'"bar')


import virt

virt.setup_host()

vm = virt.Guest(virt.GUEST_NAME_GUI)

#vm.install()
#vm.prepare_for_snapshot()
if not vm.can_be_snapshotted():
    vm.install()
    vm.prepare_for_snapshot()

with vm.snapshotted():
    vm.comm(['dd', 'if=/dev/zero', 'of=/bigf', 'bs=1M', 'count=10'])
    state = vm.comm(['ls', '/', '-l'])
    log(state.stdout)

with vm.snapshotted():
    state = vm.comm(['ls', '/', '-l'])
    log(state.stdout)

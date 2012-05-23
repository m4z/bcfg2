import os
import logging
import tempfile
import Bcfg2.Server.Plugin
from subprocess import Popen, PIPE
from Bcfg2.Server.Plugins.Cfg import CfgFilter

logger = logging.getLogger(__name__)

class CfgDiffFilter(CfgFilter):
    __extensions__ = ['diff']

    def modify_data(self, entry, metadata, data):
        basehandle, basename = tempfile.mkstemp()
        open(basename, 'w').write(data)
        os.close(basehandle)

        cmd = ["patch", "-u", "-f", basefile.name]
        patch = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stderr = patch.communicate(input=self.data)[1]
        ret = patch.wait()
        output = open(basefile.name, 'r').read()
        os.unlink(basefile.name)
        if ret != 0:
            logger.error("Error applying diff %s: %s" % (delta.name, stderr))
            raise Bcfg2.Server.Plugin.PluginExecutionError('delta', delta)
        return output

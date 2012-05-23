import sys
import logging
import Bcfg2.Server.Plugin
from Bcfg2.Server.Plugins.Cfg import CfgGenerator

logger = logging.getLogger(__name__)

try:
    import genshi.core
    from genshi.template import TemplateLoader, NewTextTemplate
    have_genshi = True
except ImportError:
    TemplateLoader = None
    have_genshi = False

# snipped from TGenshi
def removecomment(stream):
    """A genshi filter that removes comments from the stream."""
    for kind, data, pos in stream:
        if kind is genshi.core.COMMENT:
            continue
        yield kind, data, pos


class CfgGenshiGenerator(CfgGenerator):
    __extensions__ = ['genshi']
    __loader_cls__ = TemplateLoader

    def __init__(self, fname, spec, encoding):
        CfgGenerator.__init__(self, fname, spec, encoding)
        if not have_genshi:
            msg = "Cfg: Genshi is not available: %s" % fname
            logger.error(msg)
            raise Bcfg2.Server.Plugin.PluginExecutionError(msg)
        self.loader = self.__loader_cls__()
        self.template = None

    @classmethod
    def ignore(cls, event, basename=None):
        return (event.filename.endswith(".genshi_include") or
                CfgGenerator.ignore(event, basename=basename))

    def get_data(self, entry, metadata):
        fname = entry.get('realname', entry.get('name'))
        stream = \
            self.template.generate(name=fname,
                                   metadata=metadata,
                                   path=self.name).filter(removecomment)
        try:
            return stream.render('text', encoding=self.encoding,
                                 strip_whitespace=False)
        except TypeError:
            return stream.render('text', encoding=self.encoding)

    def handle_event(self, event):
        if event.code2str() == 'deleted':
            return
        CfgGenerator.handle_event(self, event)
        try:
            self.template = self.loader.load(self.name, cls=NewTextTemplate,
                                             encoding=self.encoding)
        except Exception:
            msg = "Cfg: Could not load template %s: %s" % (self.name,
                                                           sys.exc_info()[1])
            logger.error(msg)
            raise Bcfg2.Server.Plugin.PluginExecutionError(msg)
            

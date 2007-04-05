from simplegeneric import generic
from peak.util.decorators import struct

try:
    import xml.etree.cElementTree as ET
except ImportError:
    try:
        import cElementTree as ET
    except ImportError:
        import elementtree.ElementTree as ET

__all__ = [
    'DocinfoConflict', 
]

class DocinfoConflict(ValueError):
    """Attempt to set conflicting options"""

@generic
def iter_docinfo(ob):
    """Yield object(s) providing shipping document info for `ob`"""
    raise NotImplementedError("No docinfo producer registered for", type(ob))    

@iter_docinfo.when_type(list)
@iter_docinfo.when_type(tuple)
def docinfo_iterable(ob):
    for ob in ob:
        yield ob

@generic
def docinfo_to_etree(ob, etree, isdefault):
    """Update `etree` to apply document info"""
    for ob in docinfo_iterable(ob):
        docinfo_to_etree(ob, etree, isdefault)

@struct()
def _DocInfo(tag, value, attr=None):
    """Object representing DAZzle XML text or attributes"""
    return tag, value, attr


@docinfo_to_etree.when_type(_DocInfo)
def _di_to_etree(ob, etree, isdefault):
    t, tag, value, attr = ob   
    
    if tag=='DAZzle':
        el = etree
    else:
        el = etree[-1].find(tag)
        if el is None:
            el = ET.SubElement(etree[-1], tag)
            
    if attr:
        old = el.attrib.get(attr)
        set = el.attrib.__setitem__
    else:
        old = el.text
        set = lambda a, v: setattr(el, 'text', v)

    if old is not None and old<>unicode(value):
        if isdefault:
            return
        name = tag+(attr and '.'+attr or '')
        raise DocinfoConflict(
            "Can't set '%s=%s' when '%s=%s' already set" % (name,value,name,old)
        )
    set(attr, value)            


def add_packages(etree, packages, *defaults):
    for p in packages:
        ET.SubElement(etree, 'Package', ID=str(len(etree)+1))
        docinfo_to_etree(p, etree, False)
        docinfo_to_etree(defaults, etree, True)

def make_tree(packages, *defaults):
    """Create an Element subtree for `packages`, using `defaults`"""
    etree=ET.Element('DAZzle')
    add_packages(etree, packages, *defaults)
    return etree


def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        'README.txt',
        optionflags=doctest.ELLIPSIS|doctest.REPORT_ONLY_FIRST_FAILURE        
    )




































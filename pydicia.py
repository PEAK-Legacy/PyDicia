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
    'DocInfo', 'DocInfoConflict', 'Layout', 'OutputFile', 'Insurance',
    'DateAdvance', 'Today', 'Tomorrow',  'WeekendDelivery', 'HolidayDelivery',
    'NoPostage', 'Domestic', 'International', 'Shipment', 'Postcard',
    'Envelope', 'Flat', 'RectangularParcel', 'NonRectangularParcel',
    'FlatRateEnvelope', 'FlatRateBox', 'ToAddress', 'ReturnAddress',
    'RubberStamp', 'Print', 'Verify',
    # ...and many more symbols added dynamically!
]

class DocInfoConflict(ValueError):
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
def add_to_package(ob, package, isdefault):
    """Update `etree` to apply document info"""
    for ob in iter_docinfo(ob):
        add_to_package(ob, package, isdefault)


class Package:
    """The XML for a single package/label"""
    finished = False

    def __init__(self, batch):
        parent = batch.etree
        self.element = ET.SubElement(parent, 'Package', ID=str(len(parent)+1))
        self.parent = parent
        self.queue = []

    def __getitem__(self, (tag, attr)):
        if tag=='DAZzle':
            el = self.parent
        else:
            el = self.element.find(tag)
        if el is not None:
            if attr:
                return el.attrib.get(attr)
            return el.text

    def __setitem__(self, (tag, attr), value):
        if tag=='DAZzle':
            el = self.parent
        else:
            el = self.element.find(tag)
            if el is None:
                el = ET.SubElement(self.element, tag)
        if attr:
            el.attrib[attr] = unicode(value)
        else:
            el.text = unicode(value)

    def should_queue(self, data):
        if self.finished: return False
        self.queue.append(data)
        return True

    def finish(self):
        self.finished = True
        for item in self.queue: add_to_package(item, self, False)

class Batch:
    """An XML document and its corresponding package objects"""

    def __init__(self, *rules):
        self.etree = ET.Element('DAZzle')
        self.packages = []
        self.rules = rules

    def tostring(self, *args):
        return ET.tostring(self.etree, *args)

    def ship(self, *packageinfo):
        """Add `package` to batch, with error recovery"""
        etree = self.etree
        before = etree.attrib.copy()
        self.packages.append(packageinfo)
        package = Package(self)
        try:
            add_to_package((packageinfo, self.rules), package, False)
            package.finish()
        except:
            del etree[-1], self.packages[-1]
            etree.attrib = before
            raise

















class Shipment:
    """A collection of batches of packages for shipping"""

    def __init__(self, *rules):
        self.batches = []
        self.rules = rules

    def ship(self, *packageinfo):
        for batch in self.batches:
            try:
                return batch.ship(*packageinfo)
            except DocInfoConflict:
                pass                

        batch = Batch(*self.rules)
        batch.ship(*packageinfo)

        # only add the batch if the above operations were successful...
        self.batches.append(batch)






















inverses = dict(
    TRUE='FALSE', FALSE='TRUE', YES='NO', NO='YES', ON='OFF', OFF='ON'
)

class DocInfoBase(object):
    __slots__ = ()

    def __invert__(self):
        try:
            return DocInfo(self.tag, inverses[self.value], self.attr)
        except KeyError:
            raise ValueError("%r has no inverse" % (self,))

    def clone(self, value):
        return DocInfo(self.tag, value, self.attr)

    def set(self, package, isdefault=False):
        old = package[self.tag, self.attr]
        if old is not None and old<>unicode(self.value):
            if isdefault:
                return
            name = self.tag+(self.attr and '.'+self.attr or '')
            raise DocInfoConflict(
                "Can't set '%s=%s' when '%s=%s' already set" % (
                    name, self.value, name, old
                )
            )
        if self.value is not None:
            package[self.tag, self.attr] = self.value


@struct(DocInfoBase)
def DocInfo(tag, value=None, attr=None):
    """Object representing DAZzle XML text or attributes"""
    return tag, value, attr

add_to_package.when_type(DocInfo)(DocInfo.set)




def _make_symbols(d, nattr, names, factory=DocInfo, **kw):
    for name in names:
        kw[nattr] = name
        d[name] = factory(**kw)
        __all__.append(name)

def _make_globals(nattr, names, *args, **kw):
    _make_symbols(globals(), nattr, names, *args, **kw)
    __all__.extend(names)

_make_globals(
    'attr', """
    Prompt AbortOnError Test SkipUnverified AutoClose AutoPrintCustomsForms
    """.split(), tag='DAZzle', value='YES'
)
_make_globals(
    'attr', """
    RegisteredMail InsuredMail CertifiedMail RestrictedDelivery ReturnReceipt
    CertificateOfMailing DeliveryConfirmation SignatureConfirmation COD
    """.split(), tag='Services', value='ON'
)
_make_globals(
    'tag', """
    ReplyPostage BalloonRate NonMachinable OversizeRate Stealth SignatureWaiver
    NoWeekendDelivery NoHolidayDelivery ReturnToSender CustomsCertify
    """.split(), value='TRUE'
)

WeekendDelivery = ~NoWeekendDelivery
HolidayDelivery = ~NoHolidayDelivery
NoPostage = DocInfo('MailClass', 'NONE')










_make_globals(
    'tag', """
    ToName ToTitle ToCompany ToCity ToState ToPostalCode ToZIP4 ToCountry
    ToCarrierRoute ToReturnCode ToEmail ToPhone EndorsementLine ReferenceID
    ToDeliveryPoint CustomsSigner Description

    WeightOz Width Length Depth CostCenter Value
    """.split(), lambda tag: DocInfo(tag).clone
)

def Layout(filename):
    """Return a docinfo specifying the desired layout"""
    return DocInfo('DAZzle', os.path.abspath(filename), 'Layout')

def OutputFile(filename):
    """Return a docinfo specifying the desired layout"""
    return DocInfo('DAZzle', os.path.abspath(filename), 'OutputFile')


def Insurance(type):
    """Return a docinfo for UPIC or ENDICIA insurance"""
    if type not in ('UPIC', 'ENDICIA'):
        raise ValueError("Insurance() must be 'UPIC' or 'ENDICIA'")
    return DocInfo('Services', type, 'InsuredMail')

def ToAddress(*lines):
    assert len(lines)<=6
    return [DocInfo('ToAddress'+str(n+1), v) for n, v in enumerate(lines)]

def ReturnAddress(*lines):
    assert len(lines)<=6
    return [DocInfo('ReturnAddress'+str(n+1), v) for n, v in enumerate(lines)]

def RubberStamp(n, text):
    assert 1<=n<=50
    return DocInfo('RubberStamp'+str(n), text)





class Domestic:
    FirstClass = DocInfo('MailClass', 'FIRST')
    Priority   = DocInfo('MailClass', 'PRIORITY')
    ParcelPost = DocInfo('MailClass', 'PARCELPOST')
    Media      = DocInfo('MailClass', 'MEDIAMAIL')
    Library    = DocInfo('MailClass', 'LIBRARY')
    BPM        = DocInfo('MailClass', 'BOUNDPRINTEDMATTER')
    Express    = DocInfo('MailClass', 'EXPRESS')
    PresortedFirstClass = DocInfo('MailClass', 'PRESORTEDFIRST')
    PresortedStandard   = DocInfo('MailClass', 'PRESORTEDSTANDARD')

class International:
    FirstClass = DocInfo('MailClass', 'INTLFIRST')
    Priority   = DocInfo('MailClass', 'INTLPRIORITY')
    Express    = DocInfo('MailClass', 'INTLEXPRESS')
    GXG        = DocInfo('MailClass', 'INTLGXG')
    GXGNoDoc   = DocInfo('MailClass', 'INTLGXGNODOC')

Postcard             = DocInfo('PackageType', 'POSTCARD')
Envelope             = DocInfo('PackageType', 'ENVELOPE')
Flat                 = DocInfo('PackageType', 'FLAT')
RectangularParcel    = DocInfo('PackageType', 'RECTPARCEL')
NonRectangularParcel = DocInfo('PackageType', 'NONRECTPARCEL')
FlatRateEnvelope     = DocInfo('PackageType', 'FLATRATEENVELOPE')
FlatRateBox          = DocInfo('PackageType', 'FLATRATEBOX')

def DateAdvance(days):
    """Return a docinfo for the number of days ahead of time we're mailing"""
    if not isinstance(days, int) or not (0<=days<=30):
        raise ValueError("DateAdvance() must be an integer from 0-30")
    return DocInfo('DateAdvance', str(days))

Today = DateAdvance(0)
Tomorrow = DateAdvance(1)

Print  = DocInfo('DAZzle', 'PRINTING', 'Start')
Verify = DocInfo('DAZzle', 'DAZ',      'Start')




def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        'README.txt',
        optionflags = doctest.ELLIPSIS |doctest.REPORT_ONLY_FIRST_FAILURE
            | doctest.NORMALIZE_WHITESPACE
    )



































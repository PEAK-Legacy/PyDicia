import os
from decimal import Decimal
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
    'Option', 'OptionConflict', 'Shipment', 'Batch', 'iter_options',
    'DAZzle', 'Services', 'Domestic', 'International', 'Customs',
    'Insurance', 'DateAdvance', 'Today', 'Tomorrow',
    'WeekendDelivery', 'HolidayDelivery', 'NoPostage',
    'Postcard', 'Envelope', 'Flat', 'RectangularParcel',
    'NonRectangularParcel', 'FlatRateEnvelope', 'FlatRateBox',
    'ToAddress', 'ReturnAddress', 'RubberStamp',
    # ...and many more symbols added dynamically!
]

class OptionConflict(ValueError):
    """Attempt to set conflicting options"""

@generic
def iter_options(ob):
    """Yield object(s) providing shipping document info for `ob`"""
    raise NotImplementedError("No option producer registered for", type(ob))

@iter_options.when_type(list)
@iter_options.when_type(tuple)
def options_for_iterable(ob):
    for ob in ob:
        yield ob




class Package:
    """The XML for a single package/label"""
    finished = False
    total_items = total_weight = total_value = 0

    def __init__(self, batch):
        parent = batch.etree
        self.element = nested_element(parent, 'Package', ID=str(len(parent)+1))
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
                el = nested_element(self.element, tag, 2)
        if attr:
            el.attrib[attr] = unicode(value)
        else:
            el.text = unicode(value)

    def should_queue(self, data):
        if self.finished:
            return False
        self.queue.append(data)
        return True



    def add_customs_item(self, item):
        self.total_items += 1
        self.total_value += item.value * item.qty
        self.total_weight += item.weight * item.qty
        n = str()
        add_to_package(
            NumberedOptions(self.total_items,
                CustomsWeight = item.weight * item.qty,
                CustomsDescription = item.desc,
                CustomsQuantity = item.qty,
                CustomsValue = item.value * item.qty,
                CustomsCountry = item.origin
            ), self, False
        )
            
    def finish(self):
        self.finished = True

        for item in self.queue:
            add_to_package(item, self, False)

        if self.total_items:
            add_to_package(Value(self.total_value), self, False)
            from decimal import Decimal
            if self['WeightOz', None] is None:
                raise OptionConflict(
                    "Total package weight must be specified when"
                    " Customs.Items are used"
                )
            oz = Decimal(self['WeightOz', None])
            if oz < self.total_weight:
                raise OptionConflict(
                    "Total item weight is %s oz, but total package weight is"
                    " only %s oz" % (self.total_weight, oz)
                )
            if not self['CustomsFormType',None]or not self['ContentsType',None]:
                raise OptionConflict(
                    "Customs form + content type must be specified with items"
                )


class Batch:
    """An XML document and its corresponding package objects"""

    def __init__(self, *rules):
        self.etree = ET.Element('DAZzle')
        self.packages = []
        self.rules = rules

    def tostring(self, *args):
        return ET.tostring(self.etree, *args)

    def add_package(self, *packageinfo):
        """Add `package` to batch, with error recovery"""
        etree = self.etree
        before = etree.attrib.copy(), etree.text
        self.packages.append(packageinfo)
        package = Package(self)
        try:
            add_to_package((packageinfo, self.rules), package, False)
            package.finish()
        except:
            del etree[-1], self.packages[-1]
            if etree: etree[-1].tail = etree.text[:-4]
            etree.attrib, etree.text = before
            raise

def nested_element(parent, tag, indent=1, **kw):
    """Like ET.SubElement, but with pretty-printing indentation"""
    element = ET.SubElement(parent, tag, **kw)
    parent.text='\n'+'    '*indent
    element.tail = parent.text[:-4]
    if len(parent)>1:
        parent[-2].tail = parent.text
    return element







class Shipment:
    """A collection of batches of packages for shipping"""

    def __init__(self, *rules):
        self.batches = []
        self.rules = rules

    def add_package(self, *packageinfo):
        for batch in self.batches:
            try:
                return batch.add_package(*packageinfo)
            except OptionConflict:
                pass                

        batch = Batch(*self.rules)
        batch.add_package(*packageinfo)

        # only add the batch if the above operations were successful...
        self.batches.append(batch)


@generic
def add_to_package(ob, package, isdefault):
    """Update `etree` to apply document info"""
    for ob in iter_options(ob):
        add_to_package(ob, package, isdefault)















inverses = dict(
    TRUE='FALSE', FALSE='TRUE', YES='NO', NO='YES', ON='OFF', OFF='ON'
)

class OptionBase(object):
    __slots__ = ()

    def __invert__(self):
        try:
            return Option(self.tag, inverses[self.value], self.attr)
        except KeyError:
            raise ValueError("%r has no inverse" % (self,))

    def clone(self, value):
        return Option(self.tag, value, self.attr)
    __call__ = clone
    def set(self, package, isdefault=False):
        old = package[self.tag, self.attr]
        if old is not None and old<>unicode(self.value):
            if isdefault:
                return
            name = self.tag+(self.attr and '.'+self.attr or '')
            raise OptionConflict(
                "Can't set '%s=%s' when '%s=%s' already set" % (
                    name, self.value, name, old
                )
            )
        if self.value is not None:
            package[self.tag, self.attr] = self.value

    def __repr__(self):
        if self.attr:
            return "%s.%s(%r)" % (self.tag, self.attr, self.value)
        return "%s(%r)" % (self.tag, self.value)

@struct(OptionBase, __repr__ = OptionBase.__repr__.im_func)
def Option(tag, value=None, attr=None):
    """Object representing DAZzle XML text or attributes"""
    return tag, value, attr


add_to_package.when_type(Option)(Option.set)

def _make_symbols(d, nattr, names, factory=Option, **kw):
    for name in names:
        kw[nattr] = name
        d[name] = factory(**kw)

def _make_globals(nattr, names, *args, **kw):
    _make_symbols(globals(), nattr, names, *args, **kw)
    __all__.extend(names)

_make_globals(
    'tag', """
    ReplyPostage BalloonRate NonMachinable OversizeRate Stealth SignatureWaiver
    NoWeekendDelivery NoHolidayDelivery ReturnToSender CustomsCertify
    """.split(), value='TRUE'
)

_make_globals(
    'tag', """
    ToName ToTitle ToCompany ToCity ToState ToPostalCode ToZIP4 ToCountry
    ToCarrierRoute ToReturnCode ToEmail ToPhone EndorsementLine ReferenceID
    ToDeliveryPoint Description MailClass PackageType
    ContentsType CustomsFormType CustomsSigner

    WeightOz Width Length Depth CostCenter Value
    """.split(), lambda tag: Option(tag).clone
)

NoPostage = MailClass('NONE')
WeekendDelivery = ~NoWeekendDelivery
HolidayDelivery = ~NoHolidayDelivery

def NumberedOptions(n, **kw):
    n = str(n)
    return [Option(k+n, v)for k, v in kw.items()]





class Services:
    _make_symbols(
        locals(), 'attr', """
        RegisteredMail InsuredMail CertifiedMail RestrictedDelivery ReturnReceipt
        CertificateOfMailing DeliveryConfirmation SignatureConfirmation COD
        """.split(), tag='Services', value='ON'
    )

class Insurance:
    UPIC = Services.InsuredMail('UPIC')
    Endicia = Services.InsuredMail('ENDICIA')
    USPS = Services.InsuredMail
    NONE = ~USPS

def ToAddress(*lines):
    assert len(lines)<=6
    return [NumberedOptions(n+1, ToAddress=v)[0] for n, v in enumerate(lines)]

def ReturnAddress(*lines):
    assert len(lines)<=6
    return [NumberedOptions(n+1, ReturnAddress=v)[0] for n, v in enumerate(lines)]

def RubberStamp(n, text):
    assert 1<=n<=50
    return Option('RubberStamp'+str(n), text)

Postcard             = PackageType('POSTCARD')
Envelope             = PackageType('ENVELOPE')
Flat                 = PackageType('FLAT')
RectangularParcel    = PackageType('RECTPARCEL')
NonRectangularParcel = PackageType('NONRECTPARCEL')
FlatRateEnvelope     = PackageType('FLATRATEENVELOPE')
FlatRateBox          = PackageType('FLATRATEBOX')








class DAZzle:
    _make_symbols(
        locals(), 'attr', """
        Prompt AbortOnError Test SkipUnverified AutoClose AutoPrintCustomsForms
        """.split(), tag='DAZzle', value='YES'
    )
    @staticmethod
    def Layout(filename):
        """Return an option specifying the desired layout"""
        return Option('DAZzle', os.path.abspath(filename), 'Layout')
    @staticmethod   
    def OutputFile(filename):
        """Return an option specifying the desired layout"""
        return Option('DAZzle', os.path.abspath(filename), 'OutputFile')

    Start  = Option('DAZzle', attr='Start').clone
    Print  = Start('PRINTING')
    Verify = Start('DAZ')

class Domestic:
    FirstClass = MailClass('FIRST')
    Priority   = MailClass('PRIORITY')
    ParcelPost = MailClass('PARCELPOST')
    Media      = MailClass('MEDIAMAIL')
    Library    = MailClass('LIBRARY')
    BPM        = MailClass('BOUNDPRINTEDMATTER')
    Express    = MailClass('EXPRESS')
    PresortedFirstClass = MailClass('PRESORTEDFIRST')
    PresortedStandard   = MailClass('PRESORTEDSTANDARD')

class International:
    FirstClass = MailClass('INTLFIRST')
    Priority   = MailClass('INTLPRIORITY')
    Express    = MailClass('INTLEXPRESS')
    GXG        = MailClass('INTLGXG')
    GXGNoDoc   = MailClass('INTLGXGNODOC')





def DateAdvance(days):
    """Return an option for the number of days ahead of time we're mailing"""
    if not isinstance(days, int) or not (0<=days<=30):
        raise ValueError("DateAdvance() must be an integer from 0-30")
    return Option('DateAdvance', days)

Today = DateAdvance(0)
Tomorrow = DateAdvance(1)


class Customs:
    _make_symbols(
        locals(), 'value', "NONE GEM CN22 CP72".split(), CustomsFormType
    )
    _make_symbols(
        locals(), 'value',
        "Sample Gift Documents Other Merchandise ReturnedGoods".split(),
        lambda value: ContentsType(value.upper())
    )

    Signer  = CustomsSigner
    Certify = CustomsCertify

    @struct()
    def Item(desc, weight, value, qty=1, origin='United States'):
        from decimal import Decimal
        assert weight==Decimal(weight)
        assert value==Decimal(value)
        assert qty==int(qty)
        return desc, Decimal(weight), Decimal(value), int(qty), origin
    
    @add_to_package.when_type(Item)
    def _add_item(ob, package, isdefault):
        assert not isdefault, "Customs.Item objects can't be defaults"
        package.add_customs_item(ob)






def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        'README.txt',
        optionflags = doctest.ELLIPSIS |doctest.REPORT_ONLY_FIRST_FAILURE
            | doctest.NORMALIZE_WHITESPACE
    )



































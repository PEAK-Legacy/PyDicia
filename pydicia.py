import os, datetime
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
    'Option', 'OptionConflict', 'Shipment', 'Batch', 'Status',
    'add_to_package', 'iter_options', 'report_status',
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

    def __init__(self, batch, *data):
        parent = batch.etree
        self.element = nested_element(parent, 'Package', ID=str(len(parent)+1))
        self.parent = parent
        self.queue = []
        self.data = data
        if data: add_to_package(data, self, False)

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


    def __repr__(self):
        return "Package"+repr(self.data)


@generic
def report_status(ob, status):
    """Report `status` to `ob`"""
    try:
        i = iter_options(ob)
    except NotImplementedError:
        pass
    else:
        for ob in i:
            report_status(ob, status)


def convert_datetime(t):
    ymd, hms = t[:8], t[8:]
    y, m, d = int(ymd[:4]), int(ymd[4:6]), int(ymd[6:])
    if hms:
        return datetime.datetime(y,m,d,int(hms[:2]),int(hms[2:4]),int(hms[4:]))
    return datetime.date(y,m,d)


def _get_registry_string(root, path, subkey=None):
    """Return the registry value or ``None`` if not found"""
    import _winreg
    try:
        key = _winreg.OpenKey(root, path)
        try:
            return _winreg.QueryValueEx(key, subkey)[0]
        finally:
            _winreg.CloseKey(key)
    except WindowsError, e:
        if e.errno == 2:
            return None     # entry not found
        raise

l1_enc = "<?xml version='1.0' encoding='iso-8859-1'?>\n"


class Batch:
    """An XML document and its corresponding package objects"""

    filename = None

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
        try:
            package = Package(self, *packageinfo)
            add_to_package(self.rules, package, False)
            package.finish()
            self.packages.append(package)
        except:
            del etree[-1]
            if etree: etree[-1].tail = etree.text[:-4]
            etree.attrib, etree.text = before
            raise

    def write(self, tmpdir=None, encoding='latin1'):
        if self.filename is None:
            import tempfile
            outf, fname = tempfile.mkstemp('.xml.tmp', dir=tmpdir)
            self.filename = fname[:-4]
            self._set_output_file()
            os.write(outf, self.tostring(encoding))
            os.close(outf);
        else:
            self._set_output_file()
            open(self.filename+'.tmp', 'wt').write(self.tostring(encoding))
        os.rename(self.filename+'.tmp', self.filename)

    def _set_output_file(self):
        self.etree.attrib.setdefault('OutputFile', self.filename+'.output')

    def run(self):
        """Process batch synchronously, w/status retrieval and returncode"""
        self.write()
        result = DAZzle.run([self.filename])
        self.check_output()
        self.cleanup_files()
        return result

    def check_output(self):
        outputfile = self.etree.attrib.get('OutputFile')
        if outputfile and os.path.isfile(outputfile):
            txt = open(outputfile,'r').read()
            if not txt.startswith('<?'): txt = l1_enc+txt
            self.etree = ET.fromstring(txt)
            self.report_statuses()

    def cleanup_files(self):
        if self.filename:
            backupname = os.path.splitext(self.filename)[0] + '.BAK'
        else:
            backupname = None

        for fname in [
            self.etree.attrib.get('OutputFile'), self.filename, backupname
        ]:
            if fname:
                try:
                    os.unlink(fname)
                except os.error:
                    pass

    def report_statuses(self):
        for pkg in self.etree:
            if pkg.tag=='Package':
                package = self.packages[int(pkg.attrib['ID'])-1]
                package.element = pkg
                report_status(package.data, Status(package))

address_fields = (
    "ToAddress1 ToAddress2 ToAddress3 ToAddress4 ToAddress5 ToAddress6"
).split()


class Status(object):
    """A status object"""

    __slots__ = """
        Status ErrorCode ToAddress ToCity ToState ToPostalCode ToZip4 ToCountry
        ToDeliveryPoint ToCarrierRoute ToReturnCode PIC CustomsNumber
        FinalPostage TransactionID TransactionDateTime PostmarkDate
    """.split() + address_fields

    def __init__(self, package):
        for k in self.__slots__:
            setattr(self, k, package[k, None])
        self.ToAddress = filter(None,map(self.__getattribute__,address_fields))
        if self.Status and self.Status.startswith('Rejected ('):
            if self.Status.endswith(')'):
                self.ErrorCode = int(self.Status[10:-1])

        if self.FinalPostage is not None:
            self.FinalPostage = Decimal(self.FinalPostage)

        if self.PostmarkDate is not None:
            self.PostmarkDate = convert_datetime(self.PostmarkDate)

        if self.TransactionDateTime is not None:
            self.TransactionDateTime = convert_datetime(self.TransactionDateTime)
    def __str__(self):
        return '\n'.join([
            '%-20s: %r' % (k,getattr(self,k))
                for k in self.__slots__ if getattr(self,k) is not None
        ])






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

    def run(self):
        return [batch.run() for batch in self.batches]


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

try:
    from _winreg import HKEY_CURRENT_USER, HKEY_CLASSES_ROOT
except ImportError: 
    _get_registry_string = lambda *args: None
    HKEY_CURRENT_USER = HKEY_CLASSES_ROOT = None


class DAZzle:
    _make_symbols(
        locals(), 'attr', """
        Prompt AbortOnError Test SkipUnverified AutoClose AutoPrintCustomsForms
        """.split(), tag='DAZzle', value='YES'
    )
    @staticmethod
    def Layout(filename):
        """Return an option specifying the desired layout"""
        if DAZzle.LayoutDirectory:
            filename = os.path.join(DAZzle.LayoutDirectory, filename)
        return Option('DAZzle', os.path.abspath(filename), 'Layout')

    @staticmethod
    def OutputFile(filename):
        """Return an option specifying the desired layout"""
        return Option('DAZzle', os.path.abspath(filename), 'OutputFile')

    Start  = Option('DAZzle', attr='Start').clone
    Print  = Start('PRINTING')
    Verify = Start('DAZ')

    exe_path = _get_registry_string(
        HKEY_CLASSES_ROOT, 'lytfile\\shell\\open\\command'
    )

    #@staticmethod
    def get_preference(prefname):
        return _get_registry_string(
            HKEY_CURRENT_USER,
            'Software\\Envelope Manager\\dazzle\\Preferences', prefname
        )

    XMLDirectory = get_preference('XMLDirectory')
    LayoutDirectory = get_preference('LayoutDirectory')

    get_preference = staticmethod(get_preference)




    @staticmethod
    def run(args=(), sync=True):
        """Start DAZzle with arguments, returning a process or return code"""
        from subprocess import Popen
        process = Popen(
            [DAZzle.exe_path]+list(args), executable=DAZzle.exe_path
        )
        if sync:
            return process.wait()
        return process


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



































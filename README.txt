==========================================================
Package Shipment and Address Verification with ``PyDicia``
==========================================================

PyDicia is a Python interface to endicia.com's postal services client, DAZzle.
Using DAZzle's XML interface, PyDicia can be used to print shipping labels,
envelopes, postcards and more, with or without prepaid US postage indicia
(electronic stamps), as well as doing address verification.

In addition to providing a layer of syntax sugar for the DAZzle XML interface,
PyDicia provides a novel adaptive interface that lets you smoothly integrate
its functions with your application's core types (like invoice, customer, or
"packing slip" objects) without subclassing.  (This is particularly useful if
you are extending a CRM or other database that was written by somebody else.)

PyDicia uses the ElementTree, simplegeneric, and DecoratorTools packages, and
requires Python 2.4 or higher (due to use of decorators and the ``Decimal``
type).


TODO:

* global defaults

* Cmd-line and queue mode handlers

* Response parsing and application


-----------------
Developer's Guide
-----------------

Basic XML Generation
====================

PyDicia simplifies the creation of XML for DAZzle by using objects to specify
what data needs to go in the XML.  These objects are mostly ``DocInfo``
instances, or callables that create ``DocInfo`` instances.  However, the
framework is extensible, so that you can use your own object types with the
same API.  Your object types can either generate ``DocInfo`` instances, or
directly manipulate the XML using ElementTree APIs for maximum control.

In the simpler cases, however, you will just use lists or tuples of objects
provided by (or created with) the PyDicia API to represent packages or labels.


Batch Objects
-------------

XML documents are represented using ``Batch`` objects::

    >>> from pydicia import * 
    >>> b = Batch()

The ``tostring()`` method of a batch returns its XML in string form, optionally
in a given encoding (defaulting to ASCII if not specified)::

    >>> print b.tostring('latin1')
    <?xml version='1.0' encoding='latin1'?>
    <DAZzle />

To add a package to a batch, you use the ``add_package()`` method::

    >>> b.add_package(ToName('Phillip Eby'))
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
             <ToName>Phillip Eby</ToName>
        </Package>
    </DAZzle>

The ``add_package()`` method accepts zero or more objects that can manipulate
PyDicia package objects.  It also accepts tuples or lists of such objects,
nested to arbitrary depth.

    >>> b.add_package([COD, (Stealth, ToName('Ty Sarna'))], FlatRateBox)

    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <ToName>Phillip Eby</ToName>
        </Package>
        <Package ID="2">
            <Services COD="ON" />
            <Stealth>TRUE</Stealth>
            <ToName>Ty Sarna</ToName>
            <PackageType>FLATRATEBOX</PackageType>
        </Package>
    </DAZzle>

And the ``packages`` attribute of a batch keeps track of the arguments that
have been passed to ``add_package()``::

    >>> b.packages
    [(DocInfo('ToName', 'Phillip Eby', None),),
     ([DocInfo('Services', 'ON', 'COD'), (DocInfo('Stealth', 'TRUE', None),
       DocInfo('ToName', 'Ty Sarna', None))],
      DocInfo('PackageType', 'FLATRATEBOX', None))]

Each "package" in the list is a tuple of the arguments that were supplied for
each invocation of ``add_package()``.


Treating Your Objects as Packages
---------------------------------

It also accepts any custom objects of your own design, that are registered with
the ``pydicia.add_to_package()`` or ``pydicia.iter_docinfo()`` generic
functions::

    >>> class Customer:
    ...     def __init__(self, **kw):
    ...         self.__dict__ = kw

    >>> @iter_docinfo.when_type(Customer)
    ... def cust_docinfo(ob):
    ...     yield ToName(ob.name)
    ...     yield ToAddress(ob.address)
    ...     yield ToCity(ob.city)
    ...     yield ToState(ob.state)
    ...     yield ToPostalCode(ob.zip)

    >>> b = Batch()
    >>> c = Customer(
    ...     name='PJE', address='123 Nowhere Dr', state='FL', city='Nowhere',
    ...     zip='12345-6789'
    ... )
    >>> b.add_package(c)
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <ToName>PJE</ToName>
            <ToAddress1>123 Nowhere Dr</ToAddress1>
            <ToCity>Nowhere</ToCity>
            <ToState>FL</ToState>
            <ToPostalCode>12345-6789</ToPostalCode>
        </Package>
    </DAZzle>

This allows you to pass customer, package, product, invoice, or other
application-specific objects into ``add_package()``.  And the objects yielded
by your ``iter_docinfo`` implementation can also be application objects, e.g.::

    >>> class Invoice:
    ...     def __init__(self, **kw):
    ...         self.__dict__ = kw

    >>> @iter_docinfo.when_type(Invoice)
    ... def invoice_docinfo(ob):
    ...     yield ob.shippingtype
    ...     yield ob.products
    ...     yield ob.customer

    >>> b = Batch()
    >>> i = Invoice(
    ...     shippingtype=(Tomorrow, MailClass('MEDIAMAIL')),
    ...     products=[WeightOz(27),], customer=c
    ... )
    >>> b.add_package(i)
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <DateAdvance>1</DateAdvance>
            <MailClass>MEDIAMAIL</MailClass>
            <WeightOz>27</WeightOz>
            <ToName>PJE</ToName>
            <ToAddress1>123 Nowhere Dr</ToAddress1>
            <ToCity>Nowhere</ToCity>
            <ToState>FL</ToState>
            <ToPostalCode>12345-6789</ToPostalCode>
        </Package>
    </DAZzle>

Also note that there is no particular significance to my choice of lists vs.
tuples in these examples; they're more to demonstrate that you can use
arbitrary structures, as long as they contain objects that are supported by
either ``iter_docinfo()`` or ``add_to_package()``.  Normally, you will simply
use collections of either PyDicia-provided symbols, or application objects for
which you've defined an ``iter_docinfo()`` method.

You will also usually want to implement your PyDicia support in a module by
itself, so you can use ``from pydicia import *`` without worrying about symbol
collisions.


Batch-wide Options
------------------

When you create a batch, you can pass in any number of objects, to specify
options that will be applied to every package.  For example, this batch will
have every package set to be mailed tomorrow as media mail::

    >>> b = Batch( Tomorrow, MailClass('MEDIAMAIL') )
    >>> b.add_package(ToName('PJE'))
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <ToName>PJE</ToName>
            <DateAdvance>1</DateAdvance>
            <MailClass>MEDIAMAIL</MailClass>
        </Package>
    </DAZzle>


Multi-Batch Shipments
=====================

Certain DAZzle options can only be set once per file, such as the choice of
layout file.  If you are shipping multiple packages with different label
layouts (such as domestic vs. international mail), you need to separate these
packages into different batches.  The ``Shipment`` class handles this
separation for you automatically.

When you create a shipment, it initially has no batches::

    >>> s = Shipment()
    >>> s.batches
    []


But as you add packages to it, it will create batches as needed::

    >>> s.add_package(ToName('Phillip Eby'), Test)
    >>> len(s.batches)
    1

    >>> print s.batches[0].tostring()
    <DAZzle Test="YES">
        <Package ID="1">
            <ToName>Phillip Eby</ToName>
        </Package>
    </DAZzle>

As long as you're adding packages with the same or compatible options, the
same batch will be reused::

    >>> s.add_package(ToName('Ty Sarna'), Test)
    >>> len(s.batches)
    1
    >>> print s.batches[0].tostring()
    <DAZzle Test="YES">
        <Package ID="1">
            <ToName>Phillip Eby</ToName>
        </Package>
        <Package ID="2">
            <ToName>Ty Sarna</ToName>
        </Package>
    </DAZzle>

But as soon as you add a package with any incompatible options, a new batch
will be created and used::

    >>> s.add_package(ToName('PJE'), ~Test)
    >>> len(s.batches)
    2

    >>> print s.batches[1].tostring()
    <DAZzle Test="NO">
        <Package ID="1">
            <ToName>PJE</ToName>
        </Package>
    </DAZzle>
    
And each time you add a package, it's added to the first compatible batch::

    >>> s.add_package(ToName('Some Body'), ~Test)
    >>> len(s.batches)
    2

    >>> print s.batches[1].tostring()
    <DAZzle Test="NO">
        <Package ID="1">
            <ToName>PJE</ToName>
        </Package>
        <Package ID="2">
            <ToName>Some Body</ToName>
        </Package>
    </DAZzle>

    >>> s.add_package(ToName('No Body'), Test)
    >>> len(s.batches)
    2

    >>> print s.batches[0].tostring()
    <DAZzle Test="YES">
        <Package ID="1">
            <ToName>Phillip Eby</ToName>
        </Package>
        <Package ID="2">
            <ToName>Ty Sarna</ToName>
        </Package>
        <Package ID="3">
            <ToName>No Body</ToName>
        </Package>
    </DAZzle>

By the way, as with batches, you can create a shipment with options that will
be applied to all packages::

    >>> s = Shipment(Tomorrow, COD)
    >>> s.add_package(ToName('Some Body'), Test)
    >>> s.add_package(ToName('No Body'), ~Test)
    >>> len(s.batches)
    2
    >>> print s.batches[0].tostring()
    <DAZzle Test="YES">
        <Package ID="1">
            <ToName>Some Body</ToName>
            <DateAdvance>1</DateAdvance>
            <Services COD="ON" />
        </Package>
    </DAZzle>

    >>> print s.batches[1].tostring()
    <DAZzle Test="NO">
        <Package ID="1">
            <ToName>No Body</ToName>
            <DateAdvance>1</DateAdvance>
            <Services COD="ON" />
        </Package>
    </DAZzle>



Invoking DAZzle
===============


Application Integration
=======================

Status handling, Address updating, ...


Advanced Customization
======================

Using DocInfo elements, add_to_package()


-----------------
Options Reference
-----------------

Basic Package Options
=====================

MailClass(text), NoPostage

DateAdvance(), Today, Tomorrow
WeightOz(), Width(), Length(), Depth()
Value()
Description()

Addresses
=========

    >>> ToName("Phillip J. Eby")
    DocInfo('ToName', 'Phillip J. Eby', None)

    >>> ToTitle("President")
    DocInfo('ToTitle', 'President', None)

    >>> ToCompany("Dirt Simple, Inc.")
    DocInfo('ToCompany', 'Dirt Simple, Inc.', None)

    
ToAddress(*lines)
ToCity(text), ToState(text), ToPostalCode(text), ToZIP4(text), ToCountry(text)

ReturnAddress(*lines)

ToDeliveryPoint(text)
EndorsementLine(text)
ToCarrierRoute(text)
ToReturnCode(text)


Service Options
===============

FlatRateEnvelope
FlatRateBox
RectangularParcel
NonRectangularParcel
Postcard
Flat
Envelope

NonMachinable
BalloonRate

ReplyPostage
Stealth

SignatureWaiver
NoWeekendDelivery
NoHolidayDelivery
ReturnToSender

RegisteredMail

Insurance.USPS
Insurance.Endicia
Insurance.UPIC
Insurance.NONE

Domestic.

CertifiedMail
RestrictedDelivery
CertificateOfMailing
ReturnReceipt
DeliveryConfirmation
SignatureConfirmation
COD


Customs Forms
=============

Sample
Gift
Documents
Other
Merchandise

Customs.GEM(ctype, *items)
Customs.CN22(ctype, *items)
Customs.CP72(ctype, *items)

Customs(formtype, ctype, *items)

Item(desc, weight, value, qty=1, origin='United States')

CustomsSigner(text)
CustomsCertify


Processing Options
==================

Test
Layout(filename)
Print
Verify
SkipUnverified
AutoClose
Prompt
AbortOnError
AutoPrintCustomsForms


Miscellaneous
=============

RubberStamp(n, text)
ReferenceID(text)
CostCenter(int)



-------------------
Internals and Tests
-------------------

    >>> from pydicia import add_to_package, ET, DocInfo, Batch, Package

Packages::

    >>> b = Batch()
    >>> p = Package(b)

    >>> print b.tostring()
    <DAZzle>
        <Package ID="1" />
    </DAZzle>
    
    >>> Box = DocInfo('FlatRate', 'BOX')
    >>> add_to_package(Box, p, False)

    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <FlatRate>BOX</FlatRate>
        </Package>
    </DAZzle>

    >>> Envelope = DocInfo('FlatRate', 'TRUE')
    >>> add_to_package(Envelope, p, False)
    Traceback (most recent call last):
      ...
    DocInfoConflict: Can't set 'FlatRate=TRUE' when 'FlatRate=BOX' already set

    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <FlatRate>BOX</FlatRate>
        </Package>
    </DAZzle>

    >>> add_to_package(Box, p, False)
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <FlatRate>BOX</FlatRate>
        </Package>
    </DAZzle>

    >>> add_to_package(Envelope, p, True)
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <FlatRate>BOX</FlatRate>
        </Package>
    </DAZzle>
    
    >>> del p.element[-1]; p.element.text=''
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1" />
    </DAZzle>

    >>> verify_zip = DocInfo('DAZzle', 'DAZ', 'Start')

    >>> add_to_package(verify_zip, p, False)
    >>> print b.tostring()
    <DAZzle Start="DAZ">
        <Package ID="1" />
    </DAZzle>

    >>> add_to_package(DocInfo('DAZzle', 'PRINTING', 'Start'), p, False)
    Traceback (most recent call last):
      ...
    DocInfoConflict: Can't set 'DAZzle.Start=PRINTING' when 'DAZzle.Start=DAZ' already set

    >>> b = Batch()
    >>> p = Package(b)
    >>> add_to_package([verify_zip, Envelope], p, False)
    >>> print b.tostring()
    <DAZzle Start="DAZ">
        <Package ID="1">
            <FlatRate>TRUE</FlatRate>
        </Package>
    </DAZzle>

    >>> p.should_queue(COD)
    True
    >>> print b.tostring()
    <DAZzle Start="DAZ">
        <Package ID="1">
            <FlatRate>TRUE</FlatRate>
        </Package>
    </DAZzle>

    >>> p.finish()
    >>> print b.tostring()
    <DAZzle Start="DAZ">
        <Package ID="1">
            <FlatRate>TRUE</FlatRate>
            <Services COD="ON" />
        </Package>
    </DAZzle>

    >>> p.should_queue(COD)
    False


Batch rollback::

    >>> b = Batch()
    >>> print b.tostring()
    <DAZzle />

    >>> b.add_package(FlatRateEnvelope, FlatRateBox)
    Traceback (most recent call last):
      ...
    DocInfoConflict: Can't set 'PackageType=FLATRATEBOX' when
                               'PackageType=FLATRATEENVELOPE' already set

    >>> print b.tostring()  # rollback on error
    <DAZzle />


Misc shipment::

    >>> s = Shipment(verify_zip)
    >>> s.add_package(Box)
    >>> s.add_package(Envelope)
    >>> root, = s.batches
    >>> print root.tostring()
    <DAZzle Start="DAZ">
        <Package ID="1">
            <FlatRate>BOX</FlatRate>
        </Package>
        <Package ID="2">
            <FlatRate>TRUE</FlatRate>
        </Package>
    </DAZzle>


DocInfo inversion::

    >>> ~Envelope
    DocInfo('FlatRate', 'FALSE', None)
    >>> ~~Envelope
    DocInfo('FlatRate', 'TRUE', None)

    >>> ~DocInfo('Services', 'ON', 'RegisteredMail')
    DocInfo('Services', 'OFF', 'RegisteredMail')
    >>> ~~DocInfo('Services', 'ON', 'RegisteredMail')
    DocInfo('Services', 'ON', 'RegisteredMail')

    >>> ~DocInfo('DAZzle', 'YES', 'Prompt')
    DocInfo('DAZzle', 'NO', 'Prompt')
    >>> ~~DocInfo('DAZzle', 'YES', 'Prompt')
    DocInfo('DAZzle', 'YES', 'Prompt')
    

The ``iter_docinfo()`` generic function yields "docinfo" objects for an
application object.  The default implementation is to raise an error::

    >>> from pydicia import iter_docinfo

    >>> iter_docinfo(27)
    Traceback (most recent call last):
      ...
    NotImplementedError: ('No docinfo producer registered for', <type 'int'>)

And for lists and tuples, the default is to yield their contents::

    >>> list(iter_docinfo((1, 2, 3)))
    [1, 2, 3]

    >>> list(iter_docinfo(['a', 'b']))
    ['a', 'b']

This routine is used internally by ``add_to_package()``.


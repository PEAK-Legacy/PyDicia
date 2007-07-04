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

IMPORTANT
    Please note that PyDicia does not attempt to implement all of the US Postal
    Service's business rules for what options may be used in what combinations.
    It doesn't even validate most of the DAZzle client's documented
    restrictions!  So it's strictly a "Garbage In, Garbage Out" kind of deal.
    If you put garbage in, who knows what the heck will happen.  You might end
    up spending lots of money *and* getting your packages returned to you --
    and **I AM NOT RESPONSIBLE**, even if your problem is due to an error in
    PyDicia or its documentation!
    
    So, make sure you understand the shipping options you wish to use, and test
    your application thoroughly before using this code in production.  You have
    been warned!


TODO:

* Cmd-line and queue mode handlers

* Response parsing and application


-----------------
Developer's Guide
-----------------


Basic XML Generation
====================

PyDicia simplifies the creation of XML for DAZzle by using objects to specify
what data needs to go in the XML.  These objects are mostly ``Option``
instances, or callables that create ``Option`` instances.  However, the
framework is extensible, so that you can use your own object types with the
same API.  Your object types can either generate ``Option`` instances, or
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

    >>> b.add_package([Services.COD, (Stealth, ToName('Ty Sarna'))], FlatRateBox)

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
    [(ToName('Phillip Eby'),),
     ([Services.COD('ON'), (Stealth('TRUE'), ToName('Ty Sarna'))],
      PackageType('FLATRATEBOX'))]

Each "package" in the list is a tuple of the arguments that were supplied for
each invocation of ``add_package()``.


Treating Your Objects as Packages
---------------------------------

It also accepts any custom objects of your own design, that are registered with
the ``pydicia.add_to_package()`` or ``pydicia.iter_options()`` generic
functions::

    >>> class Customer:
    ...     def __init__(self, **kw):
    ...         self.__dict__ = kw

    >>> @iter_options.when_type(Customer)
    ... def cust_options(ob):
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
by your ``iter_options`` implementation can also be application objects, e.g.::

    >>> class Invoice:
    ...     def __init__(self, **kw):
    ...         self.__dict__ = kw

    >>> @iter_options.when_type(Invoice)
    ... def invoice_options(ob):
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
either ``iter_options()`` or ``add_to_package()``.  Normally, you will simply
use collections of either PyDicia-provided symbols, or application objects for
which you've defined an ``iter_options()`` method.

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

    >>> s.add_package(ToName('Phillip Eby'), DAZzle.Test)
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

    >>> s.add_package(ToName('Ty Sarna'), DAZzle.Test)
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

    >>> s.add_package(ToName('PJE'), ~DAZzle.Test)
    >>> len(s.batches)
    2

    >>> print s.batches[1].tostring()
    <DAZzle Test="NO">
        <Package ID="1">
            <ToName>PJE</ToName>
        </Package>
    </DAZzle>
    
And each time you add a package, it's added to the first compatible batch::

    >>> s.add_package(ToName('Some Body'), ~DAZzle.Test)
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

    >>> s.add_package(ToName('No Body'), DAZzle.Test)
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

    >>> s = Shipment(Tomorrow, Services.COD)
    >>> s.add_package(ToName('Some Body'), DAZzle.Test)
    >>> s.add_package(ToName('No Body'), ~DAZzle.Test)
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

XXX


Application Integration
=======================

Status handling, Address updating, ToReturnCode()... 


Advanced Customization
======================

Using Option elements, add_to_package()



-----------------
Options Reference
-----------------

Basic Package Options
=====================

MailClass(text), NoPostage

DateAdvance(), Today, Tomorrow
Value()
Description()
WeightOz()


Addresses
=========

    >>> ToName("Phillip J. Eby")
    ToName('Phillip J. Eby')

    >>> ToTitle("President")
    ToTitle('President')

    >>> ToCompany("Dirt Simple, Inc.")
    ToCompany('Dirt Simple, Inc.')

    
ToAddress(*lines)
ToCity(text), ToState(text), ToPostalCode(text), ToZIP4(text), ToCountry(text)

ReturnAddress(*lines)

ToDeliveryPoint(text)
EndorsementLine(text)
ToCarrierRoute(text)


Package Details
===============

PackageType()
FlatRateEnvelope
FlatRateBox
RectangularParcel
NonRectangularParcel
Postcard
Flat
Envelope

Width(), Length(), Depth()

NonMachinable
BalloonRate



Service Options
===============

ReplyPostage
Stealth

SignatureWaiver
NoWeekendDelivery
NoHolidayDelivery
ReturnToSender

Insurance.USPS
Insurance.Endicia
Insurance.UPIC
Insurance.NONE

Services.RegisteredMail
Services.CertifiedMail
Services.RestrictedDelivery
Services.CertificateOfMailing
Services.ReturnReceipt
Services.DeliveryConfirmation
Services.SignatureConfirmation
Services.COD

Services.InsuredMail()


Customs Forms
=============

When processing international shipments, you will usually need to specify a
customs form, contents type, and items.  Additionally, if you want to print
the customs forms already "signed", you can specify a signer and the
certification option.

Contents Types
--------------

The ``ContentsType`` constructor defines the type of contents declared on the
customs form.  There are six predefined constants for the standard contents
types::

    >>> Customs.Sample
    ContentsType('SAMPLE')

    >>> Customs.Gift
    ContentsType('GIFT')

    >>> Customs.Documents
    ContentsType('DOCUMENTS')

    >>> Customs.Other
    ContentsType('OTHER')

    >>> Customs.Merchandise
    ContentsType('MERCHANDISE')

    >>> Customs.ReturnedGoods
    ContentsType('RETURNEDGOODS')


Customs Form Types
------------------

The ``CustomsFormType`` constructor defines the type of customs form to be
used.  There are four predefined constants for the allowed form types::

    >>> Customs.GEM
    CustomsFormType('GEM')
    
    >>> Customs.CN22
    CustomsFormType('CN22')

    >>> Customs.CP72
    CustomsFormType('CP72')

    >>> Customs.NONE
    CustomsFormType('NONE')


Customs Items
-------------

Items to be declared on a customs form are created using ``Customs.Item``.
The minimum required arguments are a description, a unit weight in ounces
(which must be an integer or decimal), and a value in US dollars (also an
integer or decimal)::

    >>> from decimal import Decimal
    >>> i = Customs.Item("Paperback book", 12, Decimal('29.95'))

You may also optionally specify a quantity (which must be an integer) and a
country of origin.  The defaults for these are ``1`` and ``"United States"``,
respectively::

    >>> i
    Item('Paperback book', Decimal("12"), Decimal("29.95"), 1, 'United States')

You always specify a unit weight and value; these are automatically multiplied
by the quantity on the customs form, and for purposes of calculating total
weight/value.

Note that a package's total weight must be greater than or equal to the sum of
its items' weight, and its value must exactly equal the sum of its items'
values::

    >>> b = Batch()
    >>> b.add_package(i)
    Traceback (most recent call last):
      ...
    OptionConflict: Total package weight must be specified when Customs.Items
                    are used

    >>> b.add_package(i, WeightOz(1))
    Traceback (most recent call last):
      ...
    OptionConflict: Total item weight is 12 oz, but
                    total package weight is only 1 oz

    >>> b.add_package(i, WeightOz(12), Value(69))
    Traceback (most recent call last):
      ...
    OptionConflict: Can't set 'Value=29.95' when 'Value=69' already set

And a form type and contents type must be specified if you include any items::

    >>> b.add_package(i, WeightOz(12))
    Traceback (most recent call last):
      ...
    OptionConflict: Customs form + content type must be specified with items

    >>> b.add_package(i, WeightOz(12), Customs.Gift)
    Traceback (most recent call last):
      ...
    OptionConflict: Customs form + content type must be specified with items

    >>> b.add_package(i, WeightOz(12), Customs.CN22)
    Traceback (most recent call last):
      ...
    OptionConflict: Customs form + content type must be specified with items

    >>> b.add_package(i, WeightOz(12), Customs.Gift, Customs.CN22)
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <CustomsQuantity1>1</CustomsQuantity1>
            <CustomsCountry1>United States</CustomsCountry1>
            <CustomsDescription1>Paperback book</CustomsDescription1>
            <CustomsWeight1>12</CustomsWeight1>
            <CustomsValue1>29.95</CustomsValue1>
            <WeightOz>12</WeightOz>
            <ContentsType>GIFT</ContentsType>
            <CustomsFormType>CN22</CustomsFormType>
            <Value>29.95</Value>
        </Package>
    </DAZzle>

The final customs form will include the multiplied-out weights and values based
on the quantity of each item::

    >>> b = Batch()
    >>> b.add_package(
    ...     Customs.Item('x',23,42,3), Customs.Item('y',1,7),
    ...     WeightOz(99), Customs.Gift, Customs.CN22
    ... )
    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <CustomsQuantity1>3</CustomsQuantity1>
            <CustomsCountry1>United States</CustomsCountry1>
            <CustomsDescription1>x</CustomsDescription1>
            <CustomsWeight1>69</CustomsWeight1>
            <CustomsValue1>126</CustomsValue1>
            <CustomsQuantity2>1</CustomsQuantity2>
            <CustomsCountry2>United States</CustomsCountry2>
            <CustomsDescription2>y</CustomsDescription2>
            <CustomsWeight2>1</CustomsWeight2>
            <CustomsValue2>7</CustomsValue2>
            <WeightOz>99</WeightOz>
            <ContentsType>GIFT</ContentsType>
            <CustomsFormType>CN22</CustomsFormType>
            <Value>133</Value>
        </Package>
    </DAZzle>

    
Customs Signature
-----------------

You can specify the person who's certifying the customs form using these
options::

    >>> Customs.Signer("Phillip Eby")
    CustomsSigner('Phillip Eby')
    
    >>> Customs.Certify
    CustomsCertify('TRUE')



Processing Options
==================

DAZzle.Test
DAZzle.Layout(filename)
DAZzle.OutputFile(filename)
DAZzle.Print
DAZzle.Verify

DAZzle.SkipUnverified
DAZzle.AutoClose
DAZzle.Prompt
DAZzle.AbortOnError
DAZzle.AutoPrintCustomsForms


Miscellaneous
=============

RubberStamp(n, text)
ReferenceID(text)
CostCenter(int)



-------------------
Internals and Tests
-------------------

    >>> from pydicia import add_to_package, ET, Option, Batch, Package

Packages::

    >>> b = Batch()
    >>> p = Package(b)

    >>> print b.tostring()
    <DAZzle>
        <Package ID="1" />
    </DAZzle>
    
    >>> Box = Option('FlatRate', 'BOX')
    >>> add_to_package(Box, p, False)

    >>> print b.tostring()
    <DAZzle>
        <Package ID="1">
            <FlatRate>BOX</FlatRate>
        </Package>
    </DAZzle>

    >>> Envelope = Option('FlatRate', 'TRUE')
    >>> add_to_package(Envelope, p, False)
    Traceback (most recent call last):
      ...
    OptionConflict: Can't set 'FlatRate=TRUE' when 'FlatRate=BOX' already set

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

    >>> verify_zip = Option('DAZzle', 'DAZ', 'Start')

    >>> add_to_package(verify_zip, p, False)
    >>> print b.tostring()
    <DAZzle Start="DAZ">
        <Package ID="1" />
    </DAZzle>

    >>> add_to_package(Option('DAZzle', 'PRINTING', 'Start'), p, False)
    Traceback (most recent call last):
      ...
    OptionConflict: Can't set 'DAZzle.Start=PRINTING' when 'DAZzle.Start=DAZ' already set

    >>> b = Batch()
    >>> p = Package(b)
    >>> add_to_package([verify_zip, Envelope], p, False)
    >>> print b.tostring()
    <DAZzle Start="DAZ">
        <Package ID="1">
            <FlatRate>TRUE</FlatRate>
        </Package>
    </DAZzle>

    >>> p.should_queue(Services.COD)
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

    >>> p.should_queue(Services.COD)
    False


Batch rollback::

    >>> b = Batch()
    >>> print b.tostring()
    <DAZzle />

    >>> b.add_package(FlatRateEnvelope, FlatRateBox)
    Traceback (most recent call last):
      ...
    OptionConflict: Can't set 'PackageType=FLATRATEBOX' when
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


Option inversion::

    >>> ~Envelope
    FlatRate('FALSE')
    >>> ~~Envelope
    FlatRate('TRUE')

    >>> ~Option('Services', 'ON', 'RegisteredMail')
    Services.RegisteredMail('OFF')
    >>> ~~Option('Services', 'ON', 'RegisteredMail')
    Services.RegisteredMail('ON')

    >>> ~Option('DAZzle', 'YES', 'Prompt')
    DAZzle.Prompt('NO')
    >>> ~~Option('DAZzle', 'YES', 'Prompt')
    DAZzle.Prompt('YES')
    

The ``iter_options()`` generic function yields "option" objects for an
application object.  The default implementation is to raise an error::

    >>> from pydicia import iter_options

    >>> iter_options(27)
    Traceback (most recent call last):
      ...
    NotImplementedError: ('No option producer registered for', <type 'int'>)

And for lists and tuples, the default is to yield their contents::

    >>> list(iter_options((1, 2, 3)))
    [1, 2, 3]

    >>> list(iter_options(['a', 'b']))
    ['a', 'b']

This routine is used internally by ``add_to_package()``.


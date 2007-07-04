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

Basic Use
=========

    >>> from pydicia import * 
    >>> s = Shipment()
    >>> s.batches
    []

    >>> s.ship(ToName('Phillip Eby'), Test)
    >>> len(s.batches)
    1
    >>> s.batches[0].packages
    [(DocInfo('ToName', 'Phillip Eby', None), DocInfo('DAZzle', 'YES', 'Test'))]

    >>> print s.batches[0].tostring()
    <DAZzle Test="YES"><Package ID="1"><ToName>Phillip
    Eby</ToName></Package></DAZzle>
    
    >>> s.ship(ToName('Ty Sarna'))
    >>> len(s.batches)
    1
    >>> print s.batches[0].tostring()
    <DAZzle Test="YES"><Package ID="1"><ToName>Phillip
    Eby</ToName></Package><Package ID="2"><ToName>Ty
    Sarna</ToName></Package></DAZzle>

    >>> s.ship(ToName('PJE'), ~Test)
    >>> len(s.batches)
    2
    >>> print s.batches[1].tostring()
    <DAZzle Test="NO"><Package ID="1"><ToName>PJE</ToName></Package></DAZzle>
    


Application Integration
=======================

DocInfo yielding, Status handling, Address updating, ...


Advanced Customization
======================

Using DocInfo elements


-----------------
Options Reference
-----------------

Basic Package Options
=====================

MailClass(text), NoPostage

DateAdvance, Today, Tomorrow
WeightOz(), Width(), Length(), Depth()
Value
Description

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
    <DAZzle><Package ID="1" /></DAZzle>
    
    >>> Box = DocInfo('FlatRate', 'BOX')
    >>> add_to_package(Box, p, False)

    >>> print b.tostring()
    <DAZzle><Package ID="1"><FlatRate>BOX</FlatRate></Package></DAZzle>

    >>> Envelope = DocInfo('FlatRate', 'TRUE')
    >>> add_to_package(Envelope, p, False)
    Traceback (most recent call last):
      ...
    DocInfoConflict: Can't set 'FlatRate=TRUE' when 'FlatRate=BOX' already set

    >>> print b.tostring()
    <DAZzle><Package ID="1"><FlatRate>BOX</FlatRate></Package></DAZzle>

    >>> add_to_package(Box, p, False)
    >>> print b.tostring()
    <DAZzle><Package ID="1"><FlatRate>BOX</FlatRate></Package></DAZzle>

    >>> add_to_package(Envelope, p, True)
    >>> print b.tostring()
    <DAZzle><Package ID="1"><FlatRate>BOX</FlatRate></Package></DAZzle>
    
    >>> del p.element[-1]
    >>> print b.tostring()
    <DAZzle><Package ID="1" /></DAZzle>

    >>> verify_zip = DocInfo('DAZzle', 'DAZ', 'Start')

    >>> add_to_package(verify_zip, p, False)
    >>> print b.tostring()
    <DAZzle Start="DAZ"><Package ID="1" /></DAZzle>

    >>> add_to_package(DocInfo('DAZzle', 'PRINTING', 'Start'), p, False)
    Traceback (most recent call last):
      ...
    DocInfoConflict: Can't set 'DAZzle.Start=PRINTING' when 'DAZzle.Start=DAZ' already set

    >>> root = ET.Element('DAZzle')
    >>> pkg = ET.SubElement(root, 'Package', ID='1')
    >>> print ET.tostring(root)
    <DAZzle><Package ID="1" /></DAZzle>

    >>> b = Batch()
    >>> p = Package(b)
    >>> add_to_package([verify_zip, Envelope], p, False)
    >>> print b.tostring()
    <DAZzle Start="DAZ"><Package ID="1"><FlatRate>TRUE</FlatRate></Package></DAZzle>

    >>> p.should_queue(COD)
    True
    >>> print b.tostring()
    <DAZzle Start="DAZ"><Package ID="1"><FlatRate>TRUE</FlatRate></Package></DAZzle>
    >>> p.finish()
    >>> print b.tostring()
    <DAZzle Start="DAZ"><Package ID="1"><FlatRate>TRUE</FlatRate><Services
            COD="ON" /></Package></DAZzle>
    >>> p.should_queue(COD)
    False


Batch rollback::

    >>> b = Batch()
    >>> print b.tostring()
    <DAZzle />

    >>> b.ship(FlatRateEnvelope, FlatRateBox)
    Traceback (most recent call last):
      ...
    DocInfoConflict: Can't set 'PackageType=FLATRATEBOX' when
                               'PackageType=FLATRATEENVELOPE' already set

    >>> print b.tostring()  # rollback on error
    <DAZzle />


Misc shipment::

    >>> s = Shipment(verify_zip)
    >>> s.ship(Box)
    >>> s.ship(Envelope)
    >>> root, = s.batches
    >>> print root.tostring()
    <DAZzle Start="DAZ"><Package
    ID="1"><FlatRate>BOX</FlatRate></Package><Package
    ID="2"><FlatRate>TRUE</FlatRate></Package></DAZzle>


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


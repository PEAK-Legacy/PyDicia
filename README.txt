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
packing ticket objects) without subclassing.  (This is particularly useful if
you are extending a CRM or other database that was written by somebody else.)

PyDicia uses the ElementTree, simplegeneric, and DecoratorTools packages, and
requires Python 2.4 or higher.

TODO:

* ``~`` operator for DocInfo, make DocInfo public

* global defaults

* Cmd-line and queue mode handlers

* Response parsing and application


-----------------
Developer's Guide
-----------------

Basic Use
=========



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

DateAdvance
WeightOz
Value
Description

Addresses
=========

ToName(text), ToTitle(text), ToCompany(text)
ToAddress(*lines)
ToCity(text), ToState(text), ToPostalCode(text), ToZIP4(text), ToCountry(text)

ReturnAddress(*lines)

ToDeliveryPoint(text)
EndorsementLine(text)
ToCarrierRoute(text)
ToReturnCode(text)


Service Options
===============

DomesticFlatRateEnvelope
DomesticFlatRateBox

ReplyPostage
Stealth
Oversize
SignatureWaiver
NoWeekendDelivery
NoHolidayDelivery
ReturnToSender

RegisteredMail
Insurance.USPS
Insurance.Endicia
Insurance.UPIC
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

DocInfo applications::

    >>> from pydicia import docinfo_to_etree, ET, _DocInfo, make_tree

    >>> root = ET.Element('DAZzle')
    >>> pkg = ET.SubElement(root, 'Package', ID='1')

    >>> print ET.tostring(root)
    <DAZzle><Package ID="1" /></DAZzle>
    
    >>> Box = _DocInfo('FlatRate', 'BOX')
    >>> docinfo_to_etree(Box, root, False)

    >>> print ET.tostring(root)
    <DAZzle><Package ID="1"><FlatRate>BOX</FlatRate></Package></DAZzle>

    >>> Envelope = _DocInfo('FlatRate', 'TRUE')
    >>> docinfo_to_etree(Envelope, root, False)
    Traceback (most recent call last):
      ...
    DocinfoConflict: Can't set 'FlatRate=TRUE' when 'FlatRate=BOX' already set

    >>> print ET.tostring(root)
    <DAZzle><Package ID="1"><FlatRate>BOX</FlatRate></Package></DAZzle>

    >>> docinfo_to_etree(Box, root, False)
    >>> print ET.tostring(root)
    <DAZzle><Package ID="1"><FlatRate>BOX</FlatRate></Package></DAZzle>

    >>> docinfo_to_etree(Envelope, root, True)
    >>> print ET.tostring(root)
    <DAZzle><Package ID="1"><FlatRate>BOX</FlatRate></Package></DAZzle>
    
    >>> del pkg[-1]
    >>> print ET.tostring(root)
    <DAZzle><Package ID="1" /></DAZzle>

    >>> verify_zip = _DocInfo('DAZzle', 'DAZ', 'Start')

    >>> docinfo_to_etree(verify_zip, root, False)
    >>> print ET.tostring(root)
    <DAZzle Start="DAZ"><Package ID="1" /></DAZzle>

    >>> docinfo_to_etree(_DocInfo('DAZzle', 'PRINTING', 'Start'), root, False)
    Traceback (most recent call last):
      ...
    DocinfoConflict: Can't set 'DAZzle.Start=PRINTING' when 'DAZzle.Start=DAZ' already set

    >>> root = ET.Element('DAZzle')
    >>> pkg = ET.SubElement(root, 'Package', ID='1')
    >>> print ET.tostring(root)
    <DAZzle><Package ID="1" /></DAZzle>

    >>> docinfo_to_etree([verify_zip, Envelope], root, False)
    >>> print ET.tostring(root)
    <DAZzle Start="DAZ"><Package ID="1"><FlatRate>TRUE</FlatRate></Package></DAZzle>


    >>> root = make_tree([(Box,), (Envelope,)], verify_zip)
    >>> print ET.tostring(root) # doctest: +NORMALIZE_WHITESPACE
    <DAZzle Start="DAZ"><Package
    ID="1"><FlatRate>BOX</FlatRate></Package><Package
    ID="2"><FlatRate>TRUE</FlatRate></Package></DAZzle>


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

This routine is used internally by ``docinfo_to_etree()``.



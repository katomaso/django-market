# coding: utf-8

from django.template.defaultfilters import slugify
import xml.dom.minidom
import exceptions
import copy
from django.conf import settings

class ParseError(NOError):
    pass

class SuccessError(NOError):
    pass


def parseXML(document, type = 1):
    """Vraci slovnik vsech potrebnych atributu"""
    try:

        dom = xml.dom.minidom.parseString(document)

        if type == 1:
            return parseSXML(dom)

        if type == 2:
            return parseNOXML(dom)

        return parseSXML(dom)

    except exceptions.Exception:
        return []

def parseSXML(dom):
    """Parses szbozi XML into dictionary
       {'title', 'slug', 'manufacturer', 'link', 'description', 'category', 'subcategory', 'photos', 'price', 'price_vat', 'vat', 'price_comment'}
    """
    data = []
    vendor = dom.getElementsByTagName("SHOP")

    if len(vendor) != 1: return data
    vendor = vendor[0]

    for item in vendor.getElementsByTagName("SHOPITEM"):
        try:
            wares = {}

            # povinne casti
            wares['description'] = get_text(item.getElementsByTagName("DESCRIPTION"))
            wares['manufacturer'] = get_text(item.getElementsByTagName("MANUFACTURER"))
            wares['link'] = get_text(item.getElementsByTagName("URL"))

            dues = get_text(item.getElementsByTagName("DUES"))
            wares['price_comment'] = None
            if dues != u'':
                wares['price_comment'] = u"Další poplatky (nezahrnuje dopravu) " + dues

            categorytext = get_text(item.getElementsByTagName("CATEGORYTEXT"))
            wares['category'], wares['subcategory'] = find_categories(categorytext.split("|"))

            try:
                wares['price'] = float (get_text(item.getElementsByTagName("PRICE")))
                wares['price_vat'] = get_text(item.getElementsByTagName("PRICE_VAT"))
                wares['vat'] = get_text(item.getElementsByTagName("VAT"))

                if wares['price_vat'] == u'':
                    wares['vat'] = float(wares['vat'])
                    # normalize vat
                    if wares['vat'] > 1.0 and wares['vat'] < 2: wares['vat'] -= 1.0
                    elif wares['vat'] > 2.0: wares['vat'] = wares['vat'] / 100.0

                    wares['price_vat'] = wares['price'] * (1.0 + wares['vat'])

                else:
                    wares['price_vat'] = float(wares['price_vat'])
                    wares['vat'] = (wares['price_vat'] / wares['price']) - 1.0
                    wares['vat'] = round(wares['vat'], 2)

            except ValueError:
                raise ParseError(u"Nelze stanovit cenu produktu.")

            wares['photos'] = []
            for photo in item.getElementsByTagName("IMGURL"):
                wares['photos'].append(get_text([photo,]))


            if len(item.getElementsByTagName("PRODUCT")) != 0:
                wares['title'] = get_text(item.getElementsByTagName("PRODUCT"))
                wares['slug'] = slugify(wares['title'])
                raise SuccessError('')

            else:
                if len(item.getElementsByTagName("PRODUCTNAME")) == 0:
                    raise ParseError(u"Nelze stanovit kvalifikovaný název produktu")

                title = get_text(item.getElementsByTagName("PRODUCTNAME"))

                for variant in item.getElementsByTagName("VARIANT"):
                    ext = variant.getElementsByTagName("PRODUCTNAMEEXT")
                    if len(ext) == 0: break
                    wares['title'] = title + " " + get_text(ext)
                    wares['slug'] = slugify(wares['title'])
                    wares['photos'] = []
                    for photo in variant.getElementsByTagName("IMGURL"):
                        wares['photos'].append(get_text([photo,]))

                    data.append(copy.deepcopy(wares))

        except SuccessError:
            data.append(copy.deepcopy(wares))

        except ParseError as pe:
            # don't append anything
            pass
    #endfor

    return data

def find_categories(keywords):
    """Returns (category, subcategory). If there are no found, returns (None,None)"""
    cat_instance = None
    category = None
    subcategory = None

    for keyword in keywords:
        keyword = keyword.strip()
        if len(keyword) < 3: continue

        if keyword.islower(): keyword = keyword.capitalize()
        try:
            if category is not None:
                if settings.DEBUG: print("Trying subcategory: ", keyword)
                subcategory = Category.objects.filter(parent = category, title__contains = keyword).get()
                return (category, subcategory)

            else:
                try:
                    if settings.DEBUG: print("trying keyword: ", keyword)
                    category = Category.objects.filter(title__contains = keyword, parent__isnull = True).get()

                except Category.DoesNotExist:
                    # try to find keyword in subcategories too
                    if settings.DEBUG: print("trying subcategory even there is no category yet: ", keyword)
                    cat_instance = Category.objects.filter(title__contains = keyword)
                    # if there is only one subcategory
                    if cat_instance.count() == 1:
                        if settings.DEBUG: print("only one instance of subcategory")
                        subcategory = cat_instance.get()
                        category = subcategory.parent
                        return (category, subcategory)
                    else:
                        if settings.DEBUG: print("I have found " + str(cat_instance.count()) + " of subcategories for " + keyword)

        except Category.DoesNotExist:
            continue
    # endfor

    return (category, subcategory)



def modelize (d):
    """Vraci modely Wares, Offer vycucane ze slovniku"""
    wares = Wares(*d)
    offer = Offer(*d)
    photos = []
    for image in d['images']:
        photos.append ()
    return (None,None,[])

def parseNOXML(dom):
    return None

def get_text(nodelist):
    rc = []
    for node in nodelist:

        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)

        elif node.nodeType == node.ELEMENT_NODE:
            rc.append(get_text(node.childNodes))

    return ''.join(rc).strip()

if __name__ == '__main__':
    doc = """<SHOPITEM>
    <PRODUCT>Světélkující podložka pod myš</PRODUCT>
    <DESCRIPTION>Fosforeskující okraj, nevyžaduje baterie.</DESCRIPTION>
    <URL>http://obchod.cz/podlozky-pod-mys/fosfor</URL>
    <ITEM_TYPE>new</ITEM_TYPE>
    <DELIVERY_DATE>1</DELIVERY_DATE>
    <IMGURL>http://obchod.cz/obrazky/podlozky-pod-mys/fosfor.jpg</IMGURL>
    <PRICE>620</PRICE>
    <PRICE_VAT>756</PRICE_VAT>
    </SHOPITEM>"""

    parseString(doc)


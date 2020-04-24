Tariff
######

.. module:: multishop.tariff

Účtuje využívání služeb. Poplatků je vícero. Platby se přidávají se
vzrůstajícími možnostmi platformy.

Primární zaměření platformy je na drobné podnikatele bez eshopů a na
začínající podnikatele "startupy", kterým tak poskytujeme promo-místo kde jsou i
ostatní startupy.


Logika zpoplatnění
==================

Forma vydělávání peněz je

 * **Měsíční předplatné** za provozování obchodu pro všechny - jak ty, kteří
   mají obchod jenom zde, tak importované eshopy. U obou nám to pomáhá předejít
   situaci, kdy obchody probíhají za našimi zády. U importovaných eshopů to hrozí
   o hodně víc. Na předplatné se vztahují kupóny.

 * **Procenta z prodaného zboží** je fixní sazba pro všechny. Na tento poplatek
   se nevztahují kupóny.
   Poplatek se automaticky započítá u jakéhokoliv zboží, které se dostane v
   objednávce přes status :attr:`multishop.core.Order.CONFIRMED`. Procenta z ceny
   se předpokládá, že jsou započítané v ceně - *naše platforma cenu nenavyšuje*!

Rizika
~~~~~~

**Obchody nám budou prodávat za zády.** Tohle částečně řeší mesíční poplatek za
vedení obchodu. V případě již existujích eshopů tomu nemáme šanci zabránit.
Dlouhodobá strategie by byla donutit je opustit jejich eshop a být primárně u nás.
Na to musíme poskytovat dostatek funkcí (např. export na jiné zbožíové katalogy).
V případě lidí, kteří mají primárně obchod u nás, se bude jednat o zanedbatelné
procento zákazníků, kteří budou kupovat za zády. Hlavně se bude jednat o obchody
s velmi drahým zbožím. Zase se jedná o objemné zboží, které by nás spíš trápilo
při přepravě.



Doprava
-------

Pro nás je ideální, pokud si člověk objedná pouze z jednoho obchodu. Pak dopravu
zajistí prodejce a my jsme z obliga.
V případě objednávky z vícero obchodů, se poštovné v plné výši přesune na nás a
my zajistíme svoz zboží. Cena poštovného zůstane jako předtím - maximální
poštovné ze všech výrobků.

Je nutné dobře rozmyslet procentuální zpoplatnění prodeje, abychom vykryli
ztrátu způsobenou svozem výrobků z více obchodů k jednomu zákazníkovi.


Slevy a promo-kódy
------------------

Promo kódy si může přidat pouze obchod, který má aktivní nějaké nabídky.

Aby naše služba ožila, tak by default je kupon (musí se jim poslt emailem) pro
prvních 50 lidí co přidají produkt do svého obchodu dostanou zdarma 3 měsíce
provozu.

Tarify se přiřazují při každé změně v nabídkách obchodu. Každý tarif má maximální
cenu a kvantitu. Tyto aggregace ukazují na MAXIMÁLNÍ počet a proto se tarif mění
ve chvíli kdy této hranice není dosaženo (je exkluzivní).


Modely
======

.. module:: multishop.tariff.models

.. class:: Tariff

   Reprezentuje možné tarify v rámci obchodu. Má atribut :attr:`threshold` který
   reprezentuje hranici pro volbu tohoto tarifu. Aktuálně je to číslo, které určuje
   maximální počet :class:`multishop.core.models.Offer` na obchod.

.. class:: Billing

   Manager vyúčtování obchodu, které ví jak často vyúčtovávat a jak. Jeho metoda
   :attr:`bill` je vyvolána cronem, pokud nastane čas vyúčtování (atribut :attr:`next_billing`)

.. class:: Bill

   Je reálný doklad, který je nutné uhradit ze strany obchodu. Každý :class:`Bill` má své

.. class:: Statistics

   Se vytvoří při každé změně :class:`multishop.core.models.Offer` aby
   zachycoval historii vývoje obchodu.

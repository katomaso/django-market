.. module:: multishop.core

Core
####

.. module:: multishop.core.models

Modely
======


.. py:class:: Shop

	Model pro identifikaci obchodu, vlastníka a jeho vztah k DPH. Platby a
	objednávky jsou v samostatných modulech (tariff a checkout).

	Při importu zboží zachováváme cenu a implicite předpokládáme, že naše provize
	je tam již započítána.


TODO: dodat class diagram z multishop.dot vygenerovany jako
::bash

   pm graph_models -a > doc/multishop.dot

a na to je potreba mit django_extensions
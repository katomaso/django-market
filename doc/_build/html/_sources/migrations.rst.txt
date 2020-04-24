.. module:: multishop.migrations

Migrace
#######

.. module:: multishop.migrations

Migrace jsou tady docela komplikované. Ač jsou všechny v jednom projektu,
tak se odkazují na všechny modelu všech podprojektů. Modely mají pokaždé
definované ``app_label="multishop"``.

Flatpages
=========
Flatpages jsou modul djanga pro jednoduchý "blogging". To znamená, že prostě
renderuje stránky z databáze/templates uživateli tak jak jsou.

Pro jednodušší vývoj máme flatpages ve ``templates/flatpages/<jazyk>`` a teď
pozor! Jejich název se použije jako URL, první řádka-komentář jako nadpis,
nepovinně je zde tag ``{% extends "slozka/sablona.html" %}`` na druhé řádce,
a zbytek je tělo textu. Pokud šablona nespecifikuje ``extedns`` použije se
defaultní ``flatpages/default.html``.


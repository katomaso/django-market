multishop |version| dokumentace
###############################

Nápověda jak komentovat pythoní docstrings
http://www.sphinx-doc.org/en/stable/domains.html#info-field-lists

Příkaz pro upload balíků na pypi::

    $ python setup.py bdist_wheel --universal upload --sign -r pypi

Volbu ``--universal`` lze nahradit za implicitní volbu v setup.cfg ve formě

    [bdist_wheel]
    universal=1


.. toctree::
   :titlesonly:

   core
   tariff
   checkout
   testing
   migrations



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


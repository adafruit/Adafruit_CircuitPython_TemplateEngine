Introduction
============


.. image:: https://readthedocs.org/projects/adafruit-circuitpython-template-engine/badge/?version=latest
    :target: https://docs.circuitpython.org/projects/templateengine/en/latest/
    :alt: Documentation Status


.. image:: https://raw.githubusercontent.com/adafruit/Adafruit_CircuitPython_Bundle/main/badges/adafruit_discord.svg
    :target: https://adafru.it/discord
    :alt: Discord


.. image:: https://github.com/adafruit/Adafruit_CircuitPython_TemplateEngine/workflows/Build%20CI/badge.svg
    :target: https://github.com/adafruit/Adafruit_CircuitPython_TemplateEngine/actions
    :alt: Build Status


.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Code Style: Black

Templating engine to substitute variables into a template string. Templates can also include conditional logic and loops. Often used for web pages.

Library is highly inspired by the
`Jinja2 <https://jinja.palletsprojects.com/en/3.1.x/templates/>`_
and `Django Templates <https://docs.djangoproject.com/en/4.2/ref/templates/>`_,
but it does not implement all of their features and takes a different approach to some of them.

Main diffrences from Jinja2 and Django Templates:

- filters are not supported, and there is no plan to support them
- all variables passed inside context must be accessed using the ``context`` object
- you can call methods inside templates just like in Python
- no support for nested blocks, although inheritance is supported
- no support for custom tags

Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://circuitpython.org/libraries>`_
or individual libraries can be installed using
`circup <https://github.com/adafruit/circup>`_.



Installing from PyPI
=====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/adafruit-circuitpython-templateengine/>`_.
To install for current user:

.. code-block:: shell

    pip3 install adafruit-circuitpython-templateengine

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install adafruit-circuitpython-templateengine

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .env/bin/activate
    pip3 install adafruit-circuitpython-templateengine

Installing to a Connected CircuitPython Device with Circup
==========================================================

Make sure that you have ``circup`` installed in your Python environment.
Install it with the following command if necessary:

.. code-block:: shell

    pip3 install circup

With ``circup`` installed and your CircuitPython device connected use the
following command to install:

.. code-block:: shell

    circup install adafruit_templateengine

Or the following command to update an existing version:

.. code-block:: shell

    circup update

Usage Example
=============

`See the simpletest for an example of how to use it. <examples/templateengine_simpletest>`_.

Documentation
=============
API documentation for this library can be found on `Read the Docs <https://docs.circuitpython.org/projects/templateengine/en/latest/>`_.

For information on building library documentation, please check out
`this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_TemplateEngine/blob/HEAD/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.
